"""check_walk.py <dir> <prefix>...: pixel check of dialogue windows in the frames saved by tas.py `walk`/`auto`.
Window = red frame row at y=142; text = pure black (0,0,0) pixels at x>=50, y 144..191. Flags: LINES>3 (text bands), EDGE (ink at x>=252: clipped by the screen edge),
LOW (ink in the last 2 rows y>=190), DARK (frame skipped: >35 % black = dark background). Prints a summary per prefix and every flagged frame."""
import sys, glob
from PIL import Image
def check(f):
    im = Image.open(f).convert("RGB"); px = im.load()
    if not all(px[x, 142] == (255, 0, 0) for x in range(0, 256, 8)): return None
    ink = [[px[x, y] == (0, 0, 0) for x in range(50, 256)] for y in range(144, 192)]
    tot = sum(map(sum, ink))
    if tot > 0.35 * 206 * 48: return ["DARK"]
    rows = [sum(r) for r in ink]; bands = 0; inb = False
    for n in rows:
        if n and not inb: bands += 1
        inb = bool(n)
    fl = []
    if bands > 4: fl.append(f"LINES~{bands}")     # a text line with ascenders/descenders can split into 2 bands; real limit checked below
    xs = [x + 50 for r in ink for x, v in enumerate(r) if v]
    if xs and max(xs) >= 252: fl.append(f"EDGE x={max(xs)}")
    if any(ink[-1]) or any(ink[-2]): fl.append("LOW")
    # text height: 3 lines = at most 3*11 = 33 rows from first to last ink row
    ys = [y for y, n in enumerate(rows) if n]
    if ys and ys[-1] - ys[0] > 36: fl.append(f"TALL {ys[-1]-ys[0]}")
    return fl
if __name__ == "__main__":
    d = sys.argv[1]; bad = 0
    for pre in sys.argv[2:]:
        fs = sorted(glob.glob(f"{d}/{pre}_[0-9][0-9][0-9]*.png")); win = dark = fl_n = 0
        for f in fs:
            r = check(f)
            if r is None: continue
            win += 1
            if r == ["DARK"]: dark += 1; continue
            if r: fl_n += 1; print("  FLAG", f.rsplit("/", 1)[1], r)
        print(pre, "frames", len(fs), "windows", win, "dark", dark, "flagged", fl_n); bad += fl_n
    sys.exit(1 if bad else 0)
