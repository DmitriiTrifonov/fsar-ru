"""guide_shoot_all.py <rom> <state> <pages...>: for each Guide page start a fresh melonds-ctl (touches only work right after a fresh start),
open the page from the grid state, scroll with the pink arrow and write dumps/emu/guide/r<NN>.png (bottom screens stitched, 3 columns)."""
import sys, os, subprocess, math
sys.path.insert(0, os.path.dirname(__file__))
from PIL import Image
import ds_gfx, lz10
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); CTL = f"{ROOT}/tools/melonds-ctl/melonds-ctl"
OUT = f"{ROOT}/dumps/emu/guide"; os.makedirs(OUT, exist_ok=True)

def tile(n):
    if 4 <= n <= 11: return 16 + 32 * (n - 4), 32
    if 12 <= n <= 18: return 16 + 32 * (n - 12), 56
    if 20 <= n <= 27: return 16 + 32 * (n - 20), 104
    if 28 <= n <= 35: return 16 + 32 * (n - 28), 128
    if 36 <= n <= 43: return 16 + 32 * (n - 36), 152
    if 44 <= n <= 49: return 16 + 32 * (n - 44), 176
    raise ValueError(n)

def height(n):
    d = lz10.decompress(open(f"{ROOT}/patched_raw/Guide/ue/m_guide{n:02d}.pbg.z", "rb").read()); return len(ds_gfx.decode_indexed(d, ds_gfx.parse(d)))

def run_page(rom, state, n):
    p = subprocess.Popen([CTL], cwd=ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1)
    def c(cmd):
        p.stdin.write(cmd + "\n"); p.stdin.flush(); r = p.stdout.readline().strip()
        if not r.startswith("OK"): raise RuntimeError(f"{cmd}: {r}")
    c(f"load_rom {rom}"); c(f"load_state {state}"); c("run 30")
    x, y = tile(n); c(f"touch {x} {y}"); c("run 10"); c("release"); c("run 200")
    steps = math.ceil(height(n) / 90) + 1; files = []
    for k in range(steps):
        f = f"{OUT}/r{n:02d}_{k:02d}.ppm"; c(f"shot {f}"); files.append(f)
        c("touch 235 137"); c("run 60"); c("release"); c("run 20")
    p.stdin.write("quit\n"); p.stdin.flush(); p.terminate()
    ims = [Image.open(f) for f in files]; ims = [i.crop((0, i.height // 2, i.width, i.height)) for i in ims]
    W, H = ims[0].size; cols = 3; out = Image.new("RGB", (W * cols, H * math.ceil(len(ims) / cols)))
    for k, im in enumerate(ims): out.paste(im, ((k % cols) * W, (k // cols) * H))
    out.save(f"{OUT}/r{n:02d}.png")
    for f in files: os.remove(f)
    print(n, "steps", steps, out.size, flush=True)

if __name__ == "__main__":
    rom, state = sys.argv[1:3]
    for n in map(int, sys.argv[3:]): run_page(rom, state, n)
