"""Batch runner for the headless driver: emu_run.py <rom> "cmd; cmd; ..." (also: 'press Start', 'wait N', 'png NAME' = screenshot to dumps/emu/NAME.png)
 press <buttons> [frames] / touch X Y -> convenience; everything else goes to tools/melonds-ctl as is."""
import subprocess, sys, os
from PIL import Image
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BTN = {"A": 1, "B": 2, "SELECT": 4, "START": 8, "RIGHT": 0x10, "LEFT": 0x20, "UP": 0x40, "DOWN": 0x80, "R": 0x100, "L": 0x200, "X": 0x400, "Y": 0x800}


def run(rom, script, verbose=True):
    p = subprocess.Popen([os.path.join(ROOT, "tools/melonds-ctl/melonds-ctl")], cwd=ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1)
    def ctl(c):
        p.stdin.write(c + "\n"); p.stdin.flush(); r = p.stdout.readline().strip()
        if verbose and not r.startswith("OK"): print(c, "->", r)
        return r
    ctl(f"load_rom {rom} {os.environ['SAV']}" if os.environ.get("SAV") else f"load_rom {rom}")
    for cmd in [c.strip() for c in script.split(";") if c.strip()]:
        w = cmd.split()
        if w[0] == "press":
            m = 0
            for b in w[1].replace(",", "+").split("+"): m |= BTN[b.upper()]
            ctl(f"keys {m:x}"); ctl(f"run {int(w[2]) if len(w) > 2 else 4}"); ctl("keys 0"); ctl("run 20")
        elif w[0] == "wait": ctl(f"run {w[1]}")
        elif w[0] == "png":
            ppm = os.path.join(ROOT, "dumps/emu", w[1] + ".ppm"); ctl(f"shot {ppm}"); Image.open(ppm).save(ppm[:-4] + ".png")
        else: ctl(cmd)
    p.stdin.write("quit\n"); p.stdin.flush(); p.wait()


if __name__ == "__main__":
    run(sys.argv[1], sys.argv[2])
