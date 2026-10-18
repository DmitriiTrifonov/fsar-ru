"""gfx_frames.py Guide <page> --skel | --check | (render): boxed answer lists (white rectangle, 2 px border, text inside).
A frame = two horizontal 2-row border lines (ink run >= 200 px) bounding a text area. text/gfx/Guide/<page>.frames.tsv: id<TAB>EN<TAB>RU per frame, RU lines separated by ' // '.
Only the interior is redrawn (border stays); lines at pitch 11 with the Guide pixel font, left margin = original text start."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import gfx_blocks as G, gfx_font as F, ds_gfx, lz10
ROOT = G.ROOT; PITCH = 11

def run_len(r):
    best = run = 0
    for v in r:
        run = run + 1 if v else 0; best = max(best, run)
    return best

def find_frames(rows):
    ys = [y for y, r in enumerate(rows) if run_len(r) >= 200]
    groups = []
    for y in ys:
        if groups and y - groups[-1][-1] <= 1: groups[-1].append(y)
        else: groups.append([y])
    frames = []
    for a, b in zip(groups[0::2], groups[1::2]):
        top, bot = a[-1], b[0]     # interior = top+1 .. bot-1
        W = len(rows[0]); xs = [x for x in range(W) if rows[a[0]][x]]
        xl, xr = min(xs), max(xs)
        inner = [(y, x) for y in range(top + 1, bot) for x in range(xl + 3, xr - 2) if rows[y][x]]
        tx0 = min((x for _, x in inner), default=xl + 6)
        nl = max(1, (bot - top - 4) // PITCH + (1 if (bot - top - 4) % PITCH >= 8 else 0))
        frames.append(dict(top=top, bot=bot, xl=xl, xr=xr, tx0=tx0, n=nl))
    return frames

def tsv(page): return f"{ROOT}/text/gfx/Guide/{page}.frames.tsv"

def skeleton(page):
    d, info, rows = G.load("Guide", page); fr = find_frames(rows); old = {}
    if os.path.exists(tsv(page)):
        for ln in open(tsv(page), encoding="utf-8"):
            f = ln.rstrip("\n").split("\t")
            if len(f) >= 3 and f[0].isdigit(): old[int(f[0])] = f[1:3]
    with open(tsv(page), "w", encoding="utf-8") as fo:
        for i, f in enumerate(fr): fo.write(f"{i}\t{old.get(i, ['', ''])[0]}\t{old.get(i, ['', ''])[1]}\n")
    return fr

def load_base(page):
    """patched page from the block/line pass if it exists (frames are drawn on top of it), else the original"""
    pp = f"{ROOT}/patched_raw/Guide/ue/{page}.pbg.z"
    if os.path.exists(pp):
        d = lz10.decompress(open(pp, "rb").read()); info = ds_gfx.parse(d); return d, info, ds_gfx.decode_indexed(d, info)
    return G.load("Guide", page)

def render(page, write=True):
    d, info, rows = load_base(page); out = [r[:] for r in rows]; fr = find_frames(rows); rep = []; spec = {}
    for ln in open(tsv(page), encoding="utf-8"):
        f = ln.rstrip("\n").split("\t")
        if len(f) >= 3 and f[0].isdigit() and f[2].strip(): spec[int(f[0])] = f[2].strip()
    for i, f in enumerate(fr):
        if i not in spec: continue
        lines = [t.strip() for t in spec[i].split("//")]; lim = f["xr"] - 3 - f["tx0"]
        miss = [c for t in lines for c in F.missing(t)]
        ok = len(lines) <= f["n"] and not miss and all(F.width(t) <= lim for t in lines)
        rep.append((i, ok, max(F.width(t) for t in lines), lim, miss if miss else (len(lines), f["n"]) if len(lines) > f["n"] else []))
        for y in range(f["top"] + 1, f["bot"]):
            for x in range(f["xl"] + 3, f["xr"] - 2): out[y][x] = 0
        for k, t in enumerate(lines):
            def put(x, y):
                if f["top"] < y < f["bot"]: out[y][x] = 2
            F.draw(t, put, f["tx0"], f["top"] + 3 + PITCH * k)
    if write and rep and all(r[1] for r in rep):
        nd, _, _ = ds_gfx.repack(d, info, out)
        path = f"{ROOT}/patched_raw/Guide/ue/{page}.pbg.z"
        # keep other edits of this page (block mode output) as the base when it exists
        open(path, "wb").write(lz10.compress(nd))
    return rep

if __name__ == "__main__":
    page = sys.argv[2]
    if "--skel" in sys.argv:
        for i, f in enumerate(skeleton(page)): print(f"#{i}: y {f['top']}-{f['bot']} x {f['xl']}-{f['xr']} text_x {f['tx0']} lines<= {f['n']} width<= {f['xr']-3-f['tx0']}px")
    else:
        rep = render(page, write="--check" not in sys.argv); bad = [r for r in rep if not r[1]]
        print(page, "frames", len(rep), "BAD" if bad else "ok", [(i, f"{w}>{lim}" if not x else x) for i, ok, w, lim, x in bad])
