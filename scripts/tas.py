"""tas.py <rom> <macro.txt> [--save-dir DIR] [--sav FILE.sav]: plays a macro on the headless melonds-ctl and writes checkpoints.
Macro commands (one per line, '#' comments):
  wait N                      run N frames
  press BTN[+BTN] [N]         hold buttons for N frames (default 4), release, run 20 more frames. BTN: A B SELECT START RIGHT LEFT UP DOWN R L X Y
  touch X Y [N]               touch the bottom screen for N frames (default 6), release, run 20 more
  mash BTN N [GAP]            press BTN N times with GAP frames between presses (default 30)
  wait_pixel SCREEN X Y RRGGBB [TIMEOUT]   run frame by frame (steps of 5) until the pixel has that colour (+-8 per channel); SCREEN = top|bottom; TIMEOUT in frames (default 3000)
  wait_change SCREEN [TIMEOUT]             run until the screen differs from now by more than 2 % of its pixels (a scene change)
  checkpoint NAME             save dumps/emu/cp_NAME.ml1 (savestate) and cp_NAME.png (both screens)
  shot NAME                   screenshot only (dumps/emu/NAME.png)
  load_state FILE             load a savestate
  walk NAME COUNT [GAP]       press A COUNT times (GAP frames apart, default 90) and save a screenshot after every press: NAME_000.png ...
  auto NAME MAX [GAP] [STALL] press A up to MAX times; save a frame NAME_kkk.png only when a dialogue window (red frame row y=142) is visible and its text differs from the previous saved frame;
                              stops after STALL (default 6) presses with an unchanged screen (free-roam / choice) and writes checkpoint NAME_stall.ml1 + .png
  request N                   on Edo's request list (Заказ): page with 'Далее' and pick R-NN (3 per page), confirm with a second touch
  raw CMD...                  send a command to the driver as is
Variables: --set NAME=VALUE replaces $NAME in the macro text.
NB: the driver's `keys HEX` is the mask of PRESSED buttons; `keys 0` releases everything (0xFFF presses all twelve!)."""
import subprocess, sys, os
from PIL import Image
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BTN = {"A": 1, "B": 2, "SELECT": 4, "START": 8, "RIGHT": 0x10, "LEFT": 0x20, "UP": 0x40, "DOWN": 0x80, "R": 0x100, "L": 0x200, "X": 0x400, "Y": 0x800}

class Emu:
    def __init__(self, rom, out, sav=""):
        self.out = out; os.makedirs(out, exist_ok=True)
        self.p = subprocess.Popen([os.path.join(ROOT, "tools/melonds-ctl/melonds-ctl")], cwd=ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1)
        self.ctl(f"load_rom {rom} {sav}".strip())
    def ctl(self, c):
        self.p.stdin.write(c + "\n"); self.p.stdin.flush(); r = self.p.stdout.readline().strip()
        if not r.startswith("OK"): raise RuntimeError(f"{c} -> {r}")
        return r
    def shot(self, name=None):
        ppm = os.path.join(self.out, (name or "_tmp") + ".ppm"); self.ctl(f"shot {ppm}"); im = Image.open(ppm).convert("RGB"); im.load()
        if name: im.save(os.path.join(self.out, name + ".png"))
        os.remove(ppm); return im
    def run(self, n): self.ctl(f"run {n}")
    def mask(self, btns):
        m = 0
        for b in btns.replace(",", "+").split("+"): m |= BTN[b.upper()]
        return m

def screen(im, which): return im.crop((0, 0, 256, 192)) if which == "top" else im.crop((0, 192, 256, 384))

def play(rom, macro, out, sav="", vars_=None):
    e = Emu(rom, out, sav)
    text = open(macro, encoding="utf-8").read()
    for k, v in (vars_ or {}).items(): text = text.replace("$" + k, v)
    for n, line in enumerate(text.splitlines(), 1):
        line = line.split("#")[0].strip()
        if not line: continue
        w = line.split(); c = w[0]
        try:
            if c == "wait": e.run(int(w[1]))
            elif c == "press":
                e.ctl(f"keys {e.mask(w[1]):x}"); e.run(int(w[2]) if len(w) > 2 else 4); e.ctl("keys 0"); e.run(20)
            elif c == "mash":
                gap = int(w[3]) if len(w) > 3 else 30
                for _ in range(int(w[2])): e.ctl(f"keys {e.mask(w[1]):x}"); e.run(4); e.ctl("keys 0"); e.run(gap)
            elif c == "touch":
                e.ctl(f"touch {w[1]} {w[2]}"); e.run(int(w[3]) if len(w) > 3 else 6); e.ctl("release"); e.run(20)
            elif c == "wait_pixel":
                which, x, y, col = w[1], int(w[2]), int(w[3]), w[4]; tmo = int(w[5]) if len(w) > 5 else 3000
                want = tuple(int(col[i:i + 2], 16) for i in (0, 2, 4)); t = 0
                while True:
                    px = screen(e.shot(), which).getpixel((x, y))
                    if all(abs(a - b) <= 8 for a, b in zip(px, want)): break
                    if t >= tmo: raise TimeoutError(f"pixel {which} {x},{y} is {px}, wanted {want}")
                    e.run(5); t += 5
            elif c == "wait_change":
                which = w[1]; tmo = int(w[2]) if len(w) > 2 else 3000; base = screen(e.shot(), which); t = 0
                while True:
                    cur = screen(e.shot(), which); diff = sum(1 for a, b in zip(base.getdata(), cur.getdata()) if sum(abs(i - j) for i, j in zip(a, b)) > 40)
                    if diff > 0.02 * 256 * 192: break
                    if t >= tmo: raise TimeoutError("screen did not change")
                    e.run(5); t += 5
            elif c == "checkpoint":
                e.ctl(f"save_state {os.path.join(out, 'cp_' + w[1] + '.ml1')}"); e.shot("cp_" + w[1])
            elif c == "shot": e.shot(w[1])
            elif c == "load_state": e.ctl(f"load_state {w[1]}")
            elif c == "walk":
                gap = int(w[3]) if len(w) > 3 else 90
                for k in range(int(w[2])):
                    e.ctl("keys 1"); e.run(4); e.ctl("keys 0"); e.run(gap); e.shot(f"{w[1]}_{k:03d}")
            elif c == "auto":
                gap = int(w[3]) if len(w) > 3 else 90; stall = int(w[4]) if len(w) > 4 else 6; k = 0; still = 0; prev = None; last = None
                for _ in range(int(w[2])):
                    e.ctl("keys 1"); e.run(4); e.ctl("keys 0"); e.run(gap); im = e.shot()
                    dif = sum(1 for a, b in zip(prev.getdata(), im.getdata()) if sum(abs(i - j) for i, j in zip(a, b)) > 40) if prev is not None else 99999
                    if os.environ.get("TAS_DEBUG"): print("press", _, "diff", dif, flush=True)
                    win = im.crop((0, 138, 256, 192)); shown = all(win.getpixel((x, 4)) == (255, 0, 0) for x in range(0, 256, 8))
                    if (shown and last is not None and win.tobytes() == last) or (not shown and dif < 0.04 * 256 * 384): still += 1   # idle animation moves ~2.5 % of the pixels
                    else: still = 0
                    prev = im
                    if still >= stall:
                        e.ctl(f"save_state {os.path.join(out, w[1] + '_stall.ml1')}"); im.save(os.path.join(out, w[1] + "_stall.png")); print("stall after", _ + 1, "presses"); break
                    if shown and (last is None or win.tobytes() != last):
                        im.save(os.path.join(out, f"{w[1]}_{k:03d}.png")); k += 1; last = win.tobytes()
            elif c == "roam":   # random walker: hold a d-pad direction, press A, whenever a dialogue window shows up press A through it and save the frames
                import random; rnd = random.Random(int(w[3]) if len(w) > 3 else 1); k = 0; last = None; dirs = [0x40, 0x80, 0x10, 0x20, 0x50, 0x60, 0x90, 0xa0]
                def shown_win(im):
                    win = im.crop((0, 138, 256, 192)); return win if all(win.getpixel((x, 4)) == (255, 0, 0) for x in range(0, 256, 8)) else None
                for _ in range(int(w[2])):
                    e.ctl("keys %x" % rnd.choice(dirs)); e.run(rnd.randint(20, 90)); e.ctl("keys 0"); e.run(10)
                    e.ctl("keys 1"); e.run(4); e.ctl("keys 0"); e.run(30); im = e.shot(); win = shown_win(im); n = 0
                    while win is not None and n < 80:
                        if last is None or win.tobytes() != last: im.save(os.path.join(out, f"{w[1]}_{k:04d}.png")); k += 1; last = win.tobytes()
                        e.ctl("keys 1"); e.run(4); e.ctl("keys 0"); e.run(60); im = e.shot(); win = shown_win(im); n += 1
                    if n: e.ctl(f"save_state {os.path.join(out, w[1] + '_last.ml1')}")
                print("roam saved", k, "frames")
            elif c == "request":
                nn = int(w[1])
                for _ in range(nn // 3):
                    e.ctl("touch 28 70"); e.run(6); e.ctl("release"); e.run(100)
                y = 20 + 30 * (nn % 3)
                for _ in range(2): e.ctl(f"touch 170 {y}"); e.run(6); e.ctl("release"); e.run(120)
            elif c == "raw": e.ctl(" ".join(w[1:]))
            else: raise ValueError("unknown command")
        except Exception as ex:
            e.shot("fail_line%d" % n); print(f"{macro}:{n}: {line}: {ex} (screenshot {out}/fail_line{n}.png)"); e.p.terminate(); return 1
    e.p.stdin.write("quit\n"); e.p.stdin.flush(); e.p.wait(); print("ok", macro); return 0

if __name__ == "__main__":
    out = os.path.join(ROOT, "dumps/emu")
    if "--save-dir" in sys.argv: out = sys.argv[sys.argv.index("--save-dir") + 1]
    sav = sys.argv[sys.argv.index("--sav") + 1] if "--sav" in sys.argv else ""
    vs = dict(a.split("=", 1) for a in sys.argv[sys.argv.index("--set") + 1:] if "=" in a) if "--set" in sys.argv else {}
    sys.exit(play(sys.argv[1], sys.argv[2], out, sav, vs))
