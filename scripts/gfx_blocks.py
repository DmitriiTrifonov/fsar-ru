"""gfx_blocks.py <Guide|LostList> <page>: split a Guide page (1-bit white text on transparent index 0) into text lines and blocks.
A line = run of rows containing ink (rows separated by blank rows); a block = lines whose gap is <= GAP blank rows. Writes an overlay PNG."""
import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
import ds_gfx, lz10
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def load(kind, name):
    path = f"{ROOT}/extracted/data/{kind}/ue/{name}.pbg.z"
    d = lz10.decompress(open(path, "rb").read()); info = ds_gfx.parse(d)
    return d, info, ds_gfx.decode_indexed(d, info)

PITCH = 11

def lines_of(rows, bg=0):
    """Text lines. Rows with ink are grouped into blocks (blank rows split them), then a block is cut into lines at the
    PITCH-periodic baseline: the baseline row is the row with the highest ink count (bottom of x-height) of each line."""
    n = len(rows); h = [sum(1 for v in r if v != bg) for r in rows]
    blocks = []; y = 0
    while y < n:
        if h[y]:
            y0 = y
            while y < n and h[y]: y += 1
            blocks.append((y0, y - 1))
        else: y += 1
    out = []
    for (b0, b1) in blocks:
        # split a block into lines: strong rows (baseline: ink count large) every ~PITCH rows
        base = [yy for yy in range(b0, b1 + 1) if h[yy] >= max(h[max(b0, yy - 4):yy + 5]) and h[yy] >= 0.6 * max(h[b0:b1 + 1])]
        cuts = []; last = None
        for yy in base:
            if last is None or yy - last >= PITCH - 3: cuts.append(yy); last = yy
        if not cuts: cuts = [b0 + (b1 - b0) // 2]
        starts = [b0]
        for c0, c1 in zip(cuts, cuts[1:]):
            # boundary = the quietest row between two baselines, after the first one + 1
            starts.append(min(range(c0 + 2, c1 - 3), key=lambda yy: (h[yy], yy)))
        for k, st in enumerate(starts):
            en = (starts[k + 1] - 1) if k + 1 < len(starts) else b1
            xs = [x for yy in range(st, en + 1) for x, v in enumerate(rows[yy]) if v != bg]
            if xs: out.append(dict(y0=st, y1=en, x0=min(xs), x1=max(xs), base=cuts[k]))
    return out

if __name__ == "__main__":
    kind, name = sys.argv[1], sys.argv[2]
    d, info, rows = load(kind, name); L = lines_of(rows)
    for i, l in enumerate(L): print(i, l)
    im = Image.new("RGB", (len(rows[0]), len(rows)), (0, 0, 0)); px = im.load()
    for y, r in enumerate(rows):
        for x, v in enumerate(r):
            if v: px[x, y] = (255, 255, 255)
    dr = ImageDraw.Draw(im)
    for i, l in enumerate(L):
        dr.rectangle([l["x0"] - 1, l["y0"] - 1, l["x1"] + 1, l["y1"] + 1], outline=(255, 0, 0)); dr.text((l["x1"] + 3, l["y0"]), str(i), fill=(255, 255, 0))
    im.save(f"{ROOT}/dumps/gfx/blocks_{name}.png")
