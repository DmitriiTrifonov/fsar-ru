"""gfx_boxes.py Guide <page> [--check]: redraw short labels inside given rectangles (boxes with ISO/HP captions, schedule tables, gear labels).
Spec text/gfx/Guide/<page>.boxes.tsv: id<TAB>EN<TAB>RU<TAB>x0<TAB>y0<TAB>x1<TAB>y1<TAB>align (c = centred on the old ink / the rectangle, l = left edge of old ink).
The rectangle must hold only the old text (box borders outside). Background = most common colour of the rectangle, ink = every other colour (text colour = most common ink colour);
the old ink is erased, RU lines (separated by ' // ') are drawn at pitch 11 starting at the old ink top. Drawn on top of the patched page of the block/line pass (see gfx_frames)."""
import sys, os
from collections import Counter
sys.path.insert(0, os.path.dirname(__file__))
import gfx_blocks as G, gfx_font as F, gfx_frames as FR, ds_gfx, lz10
ROOT = G.ROOT; PITCH = 11

def tsv(page): return f"{ROOT}/text/gfx/Guide/{page}.boxes.tsv"

def render(page, write=True):
    d, info, rows = FR.load_base(page); out = [r[:] for r in rows]; rep = []; H = len(rows); W = len(rows[0])
    for ln in open(tsv(page), encoding="utf-8"):
        f = ln.rstrip("\n").split("\t")
        if len(f) < 8 or not f[0].isdigit() or not f[2].strip(): continue
        i = int(f[0]); x0, y0, x1, y1 = map(int, f[3:7]); align = f[7].strip() or "c"
        reg = Counter(rows[y][x] for y in range(y0, y1 + 1) for x in range(x0, x1 + 1)); bg = reg.most_common(1)[0][0]
        ink = [(x, y) for y in range(y0, y1 + 1) for x in range(x0, x1 + 1) if rows[y][x] != bg]
        if not ink: rep.append((i, False, 0, 0, ["no ink"])); continue
        col = Counter(rows[y][x] for x, y in ink).most_common(1)[0][0]
        ox0, ox1, oy0 = min(x for x, _ in ink), max(x for x, _ in ink), min(y for _, y in ink)
        cx = (ox0 + ox1) / 2 if align == "c" else None
        lines = [t.strip() for t in f[2].split("//")]; miss = sorted({c for t in lines for c in F.missing(t)})
        lim = x1 - x0 + 1; wmax = max(F.width(t) for t in lines)
        ok = not miss and wmax <= lim and oy0 + PITCH * (len(lines) - 1) + 8 <= y1 + 1
        rep.append((i, ok, wmax, lim, miss))
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1): out[y][x] = bg
        for k, t in enumerate(lines):
            x = round(cx - F.width(t) / 2) if align == "c" else ox0
            x = max(x0, min(x, x1 + 1 - F.width(t)))
            def put(px, py):
                if 0 <= px < W and 0 <= py < H: out[py][px] = col
            F.draw(t, put, x, oy0 + PITCH * k)
    if write and rep and all(r[1] for r in rep):
        nd, _, _ = ds_gfx.repack(d, info, out)
        open(f"{ROOT}/patched_raw/Guide/ue/{page}.pbg.z", "wb").write(lz10.compress(nd))
    return rep

if __name__ == "__main__":
    rep = render(sys.argv[2], write="--check" not in sys.argv); bad = [r for r in rep if not r[1]]
    print(sys.argv[2], "boxes", len(rep), "BAD" if bad else "ok", bad)
