"""Драйвер PCSX2 (macOS): свой изолированный профиль, PINE (память, состояния), ввод клавиатурой, снимки окна.

Свой экземпляр PCSX2 живёт в `build/pcsx2-profile/` (-datapath), настройки пользователя (~/Library/Application Support/PCSX2) не трогаем,
BIOS берётся оттуда по абсолютному пути. PINE на слоте 28012 (у обычного PCSX2 28011, не пересекаемся).
Ввод: в профиле геймпад привязан к клавишам, события шлёт `tools/pcsx2-ctl/pcsx2key` (CGEvent на pid; терминалу нужно «Универсальный доступ»).
Снимок: `screencapture -l <окно>` (нужна «Запись экрана»).
CLI: python3 -I scripts/pcsx2_ctl.py open <iso> [состояние.p2s] | press <кнопки> | shot <png> | read <addr> <n> | status | quit
"""
import configparser, os, re, shutil, signal, socket, struct, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP = Path("/Applications/PCSX2-v2.8.2.app/Contents/MacOS/PCSX2")
USER_DIR = Path.home() / "Library/Application Support/PCSX2"
PROFILE = ROOT / "build" / "pcsx2-profile"
DATA = PROFILE / "PCSX2"  # PCSX2 кладёт данные в подпапку PCSX2 внутри -datapath
KEYTOOL = ROOT / "tools/pcsx2-ctl/pcsx2key"
SLOT = 28012
PIDFILE = PROFILE / "pcsx2.pid"

# кнопка PS2 -> (имя привязки в ini, код клавиши macOS)
BUTTONS = {
    # специальные клавиши: Qt получает их по коду, буквы от CGEvent без текста не распознаются
    "CROSS": ("F13", 105), "CIRCLE": ("F14", 107), "TRIANGLE": ("F15", 113), "SQUARE": ("F16", 106),
    "START": ("F17", 64), "SELECT": ("F18", 79),
    "UP": ("Home", 115), "DOWN": ("End", 119), "LEFT": ("PageUp", 116), "RIGHT": ("PageDown", 121),
    "L1": ("F19", 80), "R1": ("F20", 90), "L2": ("Delete", 117), "R2": ("Insert", 114),
}
PADKEYS = {"CROSS": "Cross", "CIRCLE": "Circle", "TRIANGLE": "Triangle", "SQUARE": "Square", "START": "Start", "SELECT": "Select",
           "UP": "Up", "DOWN": "Down", "LEFT": "Left", "RIGHT": "Right", "L1": "L1", "R1": "R1", "L2": "L2", "R2": "R2"}
def layout():
    """Текущая раскладка macOS (буквенные привязки X/Z работают только при латинской; F-клавиши и стрелки — при любой)."""
    r = subprocess.run(["defaults", "read", "com.apple.HIToolbox", "AppleCurrentKeyboardLayoutInputSourceID"], capture_output=True, text=True)
    return r.stdout.strip()
ALIAS = {"A": "CROSS", "X": "CROSS", "B": "CIRCLE", "O": "CIRCLE", "Y": "TRIANGLE", "T": "TRIANGLE"}


def _sock_path():
    d = os.environ.get("TMPDIR") or "/tmp"
    return f"{d.rstrip('/')}/pcsx2.sock.{SLOT}"


def make_profile():
    """Собрать профиль: копия ini пользователя с PINE, клавиатурой вместо геймпада, абсолютным путём к BIOS."""
    for sub in ("inis", "sstates", "snaps", "memcards", "logs", "cache", "cheats", "patches", "resources", "textures", "inputprofiles", "videos", "covers"):
        (DATA / sub).mkdir(parents=True, exist_ok=True)
    src = USER_DIR / "inis" / "PCSX2.ini"
    cp = configparser.RawConfigParser(strict=False); cp.optionxform = str
    cp.read(src, encoding="utf-8")
    cp["Folders"]["Bios"] = str(USER_DIR / "bios")
    cp["EmuCore"]["EnablePINE"] = "true"; cp["EmuCore"]["PINESlot"] = str(SLOT)
    if "UI" in cp:
        cp["UI"]["ConfirmShutdown"] = "false"
    cp["InputSources"] = {"Keyboard": "true", "Mouse": "false", "SDL": "false", "SDLControllerEnhancedMode": "false", "SDLPS5PlayerLED": "false"}  # только клавиатура: физический геймпад пользователя не мешает
    cp["Hotkeys"] = {"Screenshot": "Keyboard/F8"}  # остальные хоткеи убраны, чтобы не пересекались с кнопками
    cp["Pad1"] = {"Type": "DualShock2", "InvertL": "0", "InvertR": "0", "Deadzone": "0", "AxisScale": "1.33", "ButtonDeadzone": "0", "PressureModifier": "0.5"}
    for b, k in PADKEYS.items():
        cp["Pad1"][k] = f"Keyboard/{BUTTONS[b][0]}"
    with open(DATA / "inis" / "PCSX2.ini", "w", encoding="utf-8") as f:
        cp.write(f, space_around_delimiters=True)
    # вторые привязки для ручной игры (у Mac-клавиатуры нет F13+): PCSX2 понимает повтор ключа в ini
    extra = {"Cross": "X", "Circle": "Z", "Triangle": "S", "Square": "A", "Start": "Return", "Select": "Backspace",
             "Up": "Up", "Down": "Down", "Left": "Left", "Right": "Right"}
    ini = DATA / "inis" / "PCSX2.ini"; out = []
    pad = False
    for ln in ini.read_text(encoding="utf-8").splitlines():
        out.append(ln)
        if ln.startswith("["): pad = ln.strip() == "[Pad1]"
        elif pad and "=" in ln:
            k = ln.split("=")[0].strip()
            if k in extra: out.append(f"{k} = Keyboard/{extra[k]}")
    ini.write_text("\n".join(out) + "\n", encoding="utf-8")


def pid():
    try:
        p = int(PIDFILE.read_text())
        os.kill(p, 0)
        return p
    except Exception:
        return None


def open_game(iso, state=None, wait=60):
    """Запустить PCSX2 (свой экземпляр) с образом; state — путь к .p2s (грузится сразу при старте)."""
    if pid(): quit_game()
    make_profile()
    args = [str(APP), "-datapath", str(PROFILE), "-nogui", "-batch"] if False else [str(APP), "-datapath", str(PROFILE), "-batch"]
    if state: args += ["-statefile", str(Path(state).resolve())]
    args += ["--", str(Path(iso).resolve())]
    logf = open(PROFILE / "launch.log", "w")
    p = subprocess.Popen(args, stdout=logf, stderr=subprocess.STDOUT, cwd=str(ROOT))
    PIDFILE.write_text(str(p.pid))
    t0 = time.time()
    while time.time() - t0 < wait:
        try:
            if pine_status() in (0, 1): return f"OK pid {p.pid}"
        except Exception: pass
        time.sleep(1)
    raise RuntimeError("PCSX2 не ответил по PINE за %d с (см. build/pcsx2-profile/launch.log)" % wait)


def quit_game():
    p = pid()
    if p:
        try: os.kill(p, signal.SIGTERM)
        except Exception: pass
        for _ in range(30):
            try: os.kill(p, 0); time.sleep(0.2)
            except Exception: break
        else:
            os.kill(p, signal.SIGKILL)
    try: PIDFILE.unlink()
    except Exception: pass
    return "OK"


# ---- PINE ----
def _pine(payload: bytes, expect_extra=True):
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM); s.settimeout(20)
    s.connect(_sock_path())
    try:
        s.sendall(struct.pack("<I", len(payload) + 4) + payload)
        hdr = b""
        while len(hdr) < 4:
            c = s.recv(4 - len(hdr));
            if not c: raise RuntimeError("PINE: соединение закрыто")
            hdr += c
        n = struct.unpack("<I", hdr)[0]; body = b""
        while len(body) < n - 4:
            c = s.recv(min(65536, n - 4 - len(body)))
            if not c: raise RuntimeError("PINE: обрыв ответа")
            body += c
    finally:
        s.close()
    if body[0] != 0: raise RuntimeError("PINE: команда не выполнена (игра не запущена или адрес недоступен)")
    return body[1:]


def pine_status():
    return struct.unpack("<I", _pine(bytes([0xF])))[0]  # 0 идёт, 1 пауза, 2 нет игры


def read_mem(addr, n):
    """Прочитать n байт EE-памяти (адрес 0..0x01FFFFFF) пачками Read64 (+хвост Read8)."""
    out = bytearray(); a = addr
    while n > 0:
        take = min(n, 8 * 40000)
        q = take // 8; cmds = b"".join(bytes([3]) + struct.pack("<I", a + 8 * i) for i in range(q)); tail = take - q * 8
        cmds += b"".join(bytes([0]) + struct.pack("<I", a + 8 * q + j) for j in range(tail))
        r = _pine(cmds)
        out += r[:8 * q] + r[8 * q:8 * q + tail]
        a += take; n -= take
    return bytes(out)


def write_mem(addr, data: bytes):
    cmds = b"".join(bytes([4]) + struct.pack("<I", addr + i) + bytes([b]) for i, b in enumerate(data))
    _pine(cmds)


def save_state(slot): _pine(bytes([9, slot])); return "OK"
def load_state(slot): _pine(bytes([0xA, slot])); return "OK"
def title(): r = _pine(bytes([0xB])); return r[4:].rstrip(b"\0").decode("utf-8", "replace")


# ---- ввод и снимки ----
def _buttons(s):
    out = []
    for b in re.split(r"[+,\s]+", s.strip()):
        if not b: continue
        b = ALIAS.get(b.upper(), b.upper())
        if b not in BUTTONS: raise ValueError(f"неизвестная кнопка {b!r}; есть: {', '.join(BUTTONS)} (A=Cross, B=Circle)")
        out.append(b)
    return out


def focus():
    """Вывести окно своего PCSX2 на передний план: без активного окна Qt не передаёт игре кнопки (хоткеи работают и так)."""
    p = pid()
    if p: subprocess.run(["osascript", "-e", f'tell application "System Events" to set frontmost of (first process whose unix id is {p}) to true'], capture_output=True)


def press(buttons, hold_ms=120, wait_ms=500):
    p = pid()
    if not p: raise RuntimeError("PCSX2 не запущен (open)")
    bs = _buttons(buttons)
    focus()
    for b in bs: subprocess.run([str(KEYTOOL), "key", str(p), str(BUTTONS[b][1]), "down"], check=True)
    time.sleep(hold_ms / 1000)
    for b in bs: subprocess.run([str(KEYTOOL), "key", str(p), str(BUTTONS[b][1]), "up"], check=True)
    time.sleep(wait_ms / 1000)
    return "OK"


def window_id():
    p = pid()
    if not p: raise RuntimeError("PCSX2 не запущен")
    r = subprocess.run([str(KEYTOOL), "win", str(p)], capture_output=True, text=True)
    if r.returncode: raise RuntimeError("окно PCSX2 не найдено")
    return int(r.stdout.split()[0])


def shot(path, wait=6.0):
    """Снимок кадра игры: хоткей F8 самого PCSX2 (не требует права «Запись экрана»), PNG копируется в path."""
    p = pid()
    if not p: raise RuntimeError("PCSX2 не запущен")
    snaps = DATA / "snaps"; before = set(snaps.glob("*.png"))
    subprocess.run([str(KEYTOOL), "tap", str(p), "100", "80"], check=True)  # F8
    t0 = time.time()
    while time.time() - t0 < wait:
        new = set(snaps.glob("*.png")) - before
        if new:
            f = max(new, key=lambda x: x.stat().st_mtime)
            for _ in range(240):  # PCSX2 пишет PNG медленно, ждём конца файла (чанк IEND)
                if f.stat().st_size > 100 and f.read_bytes()[-8:] == b"IEND\xaeB`\x82": break
                time.sleep(0.25)
            Path(path).parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(f, path); return str(Path(path).resolve())
        time.sleep(0.2)
    raise RuntimeError("снимок F8 не появился (игра на паузе или окно не принимает клавиши)")



def dump_state(outdir, slot=9, parts=("eeMemory.bin", "GS.bin")):
    """Сохранить состояние в слот, распаковать части (EE RAM 32 МБ, видеопамять GS) в outdir. Возвращает пути."""
    outdir = Path(outdir); outdir.mkdir(parents=True, exist_ok=True)
    ss = DATA / "sstates"
    for f in ss.glob(f"*.{slot:02d}.p2s"): f.unlink()
    save_state(slot)
    t0 = time.time(); f = None
    while time.time() - t0 < 60:
        c = list(ss.glob(f"*.{slot:02d}.p2s"))
        if c and subprocess.run(["7zz", "t", str(c[0])], capture_output=True).returncode == 0: f = c[0]; break
        time.sleep(0.5)
    if not f: raise RuntimeError("состояние не записалось")
    shutil.copyfile(f, outdir / "state.p2s")
    subprocess.run(["7zz", "x", "-y", f"-o{outdir}", str(f), *parts], capture_output=True, check=True)
    return [str(outdir / x) for x in ("state.p2s", *parts)]


if __name__ == "__main__":
    c, a = sys.argv[1], sys.argv[2:]
    if c == "open": print(open_game(a[0], a[1] if len(a) > 1 else None))
    elif c == "press": print(press(a[0], *(int(x) for x in a[1:])))
    elif c == "shot": print(shot(a[0]))
    elif c == "read": print(read_mem(int(a[0], 16), int(a[1])).hex())
    elif c == "status": print(pine_status(), title())
    elif c == "save": print(save_state(int(a[0])))
    elif c == "load": print(load_state(int(a[0])))
    elif c == "dump": print(dump_state(a[0], *(int(x) for x in a[1:])))
    elif c == "quit": print(quit_game())
    else: print(__doc__)
