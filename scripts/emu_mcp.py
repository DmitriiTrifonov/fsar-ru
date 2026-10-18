"""MCP server: headless melonDS (tools/melonds-ctl) for testing the translation. Run by Claude Code over stdio (see .mcp.json).
Tools: emu_open, emu_run, emu_press, emu_touch, emu_screenshot, emu_load_state, emu_save_state, emu_read_mem, emu_find_text, emu_script."""
import io, os, subprocess, threading
from pathlib import Path
from mcp.server.fastmcp import FastMCP, Image
from PIL import Image as PILImage

ROOT = Path(__file__).resolve().parent.parent
CTL = ROOT / "tools" / "melonds-ctl" / "melonds-ctl"
TMP = ROOT / "dumps" / "emu"
BUTTONS = {"A": 0x1, "B": 0x2, "SELECT": 0x4, "START": 0x8, "RIGHT": 0x10, "LEFT": 0x20, "UP": 0x40, "DOWN": 0x80, "R": 0x100, "L": 0x200, "X": 0x400, "Y": 0x800}

mcp = FastMCP("fsar-emu")
_proc = None
_lock = threading.Lock()


def _ctl(cmd: str) -> str:
    """Send one command to melonds-ctl and return its reply line (starts with OK / ERR)."""
    global _proc
    with _lock:
        if _proc is None or _proc.poll() is not None:
            if not CTL.exists():
                raise RuntimeError("tools/melonds-ctl/melonds-ctl не собран: запусти tools/melonds-ctl/build.sh")
            _proc = subprocess.Popen([str(CTL)], cwd=str(ROOT), stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1)
        _proc.stdin.write(cmd + "\n"); _proc.stdin.flush()
        line = _proc.stdout.readline().strip()
    if not line: raise RuntimeError("драйвер не ответил (упал?). Вызови emu_open заново")
    if line.startswith("ERR"): raise RuntimeError(line)
    return line


def _mask(buttons: str) -> int:
    m = 0
    for b in buttons.replace(",", "+").split("+"):
        b = b.strip().upper()
        if b and b not in BUTTONS: raise ValueError(f"неизвестная кнопка {b!r}; есть: {', '.join(BUTTONS)}")
        m |= BUTTONS.get(b, 0)
    return m


@mcp.tool()
def emu_open(rom: str = "build/fsar-test.nds", save: str = "") -> str:
    """Запустить (или перезапустить) безголовый эмулятор DS с ромом (путь от корня проекта). Прямой старт, окна нет. Состояния .ml1 берутся с тем же ромом, на котором сняты."""
    return _ctl(f"load_rom {rom} {save}".strip())


@mcp.tool()
def emu_run(frames: int = 60) -> str:
    """Прогнать N кадров без ограничения скорости (60 кадров = 1 секунда игры, ~200-300 кадров/с реальных)."""
    return _ctl(f"run {int(frames)}")


@mcp.tool()
def emu_press(buttons: str, frames: int = 4, wait_after: int = 30) -> str:
    """Нажать кнопки DS на `frames` кадров, отпустить и прогнать ещё `wait_after` кадров. buttons: A B Select Start Right Left Up Down R L X Y, комбинация через + (например 'A' или 'Up+A')."""
    _ctl(f"keys {_mask(buttons):x}"); _ctl(f"run {int(frames)}"); _ctl("keys 0")
    return _ctl(f"run {int(wait_after)}") if wait_after else "OK"


@mcp.tool()
def emu_touch(x: int, y: int, frames: int = 6, wait_after: int = 30) -> str:
    """Коснуться нижнего экрана в точке (x 0..255, y 0..191) на `frames` кадров, затем отпустить и прогнать `wait_after` кадров."""
    _ctl(f"touch {int(x)} {int(y)}"); _ctl(f"run {int(frames)}"); _ctl("release")
    return _ctl(f"run {int(wait_after)}") if wait_after else "OK"


@mcp.tool()
def emu_screenshot(screen: str = "both", scale: int = 2) -> Image:
    """Скриншот: screen = 'both' (верх над низом), 'top' или 'bottom'; scale = целый множитель (по умолчанию 2)."""
    TMP.mkdir(parents=True, exist_ok=True); path = TMP / "_mcp_shot.ppm"
    _ctl(f"shot {path}")
    im = PILImage.open(path).convert("RGB")
    if screen == "top": im = im.crop((0, 0, 256, 192))
    elif screen == "bottom": im = im.crop((0, 192, 256, 384))
    elif screen != "both": raise ValueError("screen: both | top | bottom")
    if scale > 1: im = im.resize((im.width * scale, im.height * scale), PILImage.NEAREST)
    buf = io.BytesIO(); im.save(buf, "PNG")
    return Image(data=buf.getvalue(), format="png")


@mcp.tool()
def emu_load_state(path: str) -> str:
    """Загрузить сейвстейт melonDS (.ml1 и т. п., путь от корня проекта). Сначала должен быть открыт тот же ром (emu_open). Копируй чужие .ml* перед загрузкой не нужно: файл только читается."""
    return _ctl(f"load_state {path}")


@mcp.tool()
def emu_save_state(path: str) -> str:
    """Сохранить сейвстейт драйвера в файл (формат совместим с melonDS 1.1)."""
    return _ctl(f"save_state {path}")


@mcp.tool()
def emu_read_mem(addr: str, length: int = 64) -> str:
    """Прочитать память шины ARM9 (адрес в hex, например 0x022EE754): hex-дамп."""
    return _ctl(f"read9 {addr.replace('0x', '')} {int(length)}")


@mcp.tool()
def emu_find_text(text: str) -> str:
    """Найти текст (латиница/ASCII, как UTF-16LE) в основной RAM (0x02000000..0x02400000): адреса вхождений."""
    return _ctl(f"find {text}")


@mcp.tool()
def emu_script(commands: str) -> str:
    """Выполнить несколько команд драйвера (по одной на строку: run N, keys HEX, touch X Y, release, shot FILE, load_state F, ...) и вернуть ответы. Для макросов."""
    return "\n".join(f"{c.strip()} -> {_ctl(c.strip())}" for c in commands.splitlines() if c.strip())


if __name__ == "__main__":
    mcp.run()
