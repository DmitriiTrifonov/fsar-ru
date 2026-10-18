"""gfx_lines.py Guide <page> --skel | --check | (render): line-by-line pages (tables of contents with icons, leader lines and page numbers).
text/gfx/Guide/<page>.lines.tsv: id<TAB>EN<TAB>RU per text line. The text part is replaced; icon (circled digit), leader line and number stay."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import gfx_blocks as G, gfx_font as F, ds_gfx, lz10

ROOT = G.ROOT; INK = 2

ICON_PAGES = {"m_guide05": 250}     # page -> first y where lines start with a circled-number icon (title lines above are plain text)

def analyse(rows, l, icons=False, strict=False, dotted_ok=False):
    if icons and l["y0"] < icons: icons = False
    """-> dict(icon_x1, tx0, xs, xe, num_x0, yl) for a line: icon end, text start, leader span, number start"""
    y0, y1, W = l["y0"], l["y1"], len(rows[0])
    yl = None; xs = xe = None
    for y in range(y1, y0 + 2, -1):
        run = 0; best = (0, 0, 0)
        for x in range(W + 1):
            v = x < W and rows[y][x]
            if v: run += 1
            else:
                if run > best[0]: best = (run, x - run, x - 1)
                run = 0
        if (best[0] >= (40 if strict else 10) and (not strict or best[2] >= l["x1"] - 16)) or (not strict and best[0] >= 4 and best[2] >= 235 and best[1] >= 200): yl, xs, xe = y, best[1], best[2]; break
    dotted = None
    if yl is None and (not strict or dotted_ok):
        for y in range(y1, y0 + 2, -1):
            xs_ = [x for x in range(W) if rows[y][x] and not (x > 0 and rows[y][x - 1]) and not (x + 1 < W and rows[y][x + 1])]
            best = None
            for i in range(len(xs_)):
                for j in range(i + 7, len(xs_)):
                    st = xs_[i + 1] - xs_[i]
                    if 2 <= st <= 8 and all(xs_[k + 1] - xs_[k] == st for k in range(i, j)):
                        if best is None or xs_[j] - xs_[i] > best[1] - best[0]: best = (xs_[i], xs_[j], st)
            if best and best[1] - best[0] >= 60: yl, xs, xe = y, best[0], best[1]; dotted = best[2]; break
    cols = sorted({x for y in range(y0, y1 + 1) for x in range(W) if rows[y][x] and (yl is None or y != yl)})
    # clusters of columns (gap >= 4 splits)
    cl = []
    for x in cols:
        if cl and x - cl[-1][1] <= 3: cl[-1][1] = x
        else: cl.append([x, x])
    icon_x1 = -1; tx0 = cols[0] if cols else 0
    def icon_rows(c): return sum(1 for y in range(y0, y1 + 1) if any(rows[y][x] for x in range(c[0], c[1] + 1)))
    if icons and len(cl) > 1 and cl[0][1] - cl[0][0] <= 12 and cl[0][0] < 8 and cl[1][0] - cl[0][1] <= 12 and l["y1"] - l["y0"] >= 8 and cl[0][1] - cl[0][0] >= 7 and icon_rows(cl[0]) >= 9:
        icon_x1 = cl[0][1]; tx0 = min(cl[1][0], icon_x1 + 7)
    elif icons and cl and cl[0][0] <= 6 and cl[0][1] - cl[0][0] > 13 and l["y1"] - l["y0"] >= 8:   # icon touching the text
        later = [x for x in cols if x >= 14]
        if later: icon_x1 = 12; tx0 = min(later[0], 19)
    num_x0 = None
    if xs is not None:
        after = [x for x in cols if x > xe]
        num_x0 = min(after) if after else None
    return dict(erase_x0=(icon_x1 + 2 if icon_x1 >= 0 else tx0), icon_x1=icon_x1, tx0=tx0, xs=xs, xe=xe, num_x0=num_x0, yl=yl, dotted=dotted)

def lines_info(rows, icons=False):
    L = G.lines_of(rows)
    # cap-top row of every line: runs of lines at a pitch of 11 share one alignment (the smallest y0 - 11k, i.e. a line with caps)
    k = 0
    for i, l in enumerate(L):
        if i and abs(l["y0"] - L[i - 1]["y0"] - 11) <= 1: k += 1
        else:
            k = 0; run = [i]
        l["_run"] = (i - k, k)
    runs = {}
    for i, l in enumerate(L): runs.setdefault(l["_run"][0], []).append((l["_run"][1], l["y0"]))
    for l in L:
        r = runs[l["_run"][0]]; off = min(y0 - 11 * kk for kk, y0 in r)
        l["r0"] = off + 11 * l["_run"][1]
    return [(l, analyse(rows, l, icons)) for l in L]

def skeleton(name):
    d, info, rows = G.load("Guide", name); L = lines_info(rows, ICON_PAGES.get(name, 0))
    p = f"{ROOT}/text/gfx/Guide/{name}.lines.tsv"; old = {}
    if os.path.exists(p):
        for ln in open(p, encoding="utf-8"):
            f = ln.rstrip("\n").split("\t")
            if len(f) >= 3 and f[0].isdigit(): old[int(f[0])] = f[1:3]
    with open(p, "w", encoding="utf-8") as fo:
        for i, (l, a) in enumerate(L): fo.write(f"{i}\t{old.get(i, ['', ''])[0]}\t{old.get(i, ['', ''])[1]}\n")
    return L

def fits(l, a, ru, W):
    limit = (a["num_x0"] - 9) if a["xs"] is not None and a["num_x0"] else (a["xe"] - 30 if a["xs"] is not None else W - 4)   # a leader without a number may start later
    w = F.width(ru)
    return a["tx0"] + w <= limit and not F.missing(ru), a["tx0"] + w, limit

def draw_item(out, l, a, ru, color=INK):
    """replace the text part of one line (leader and number stay; the leader is redrawn from the new text end)"""
    W = len(out[0]); tx0 = a["tx0"]; w = F.width(ru)
    xe_text = (a["xs"] - 1) if a["xs"] is not None else W - 1
    for y in range(l["y0"], l["y1"] + 1):
        for x in range(a.get("erase_x0", tx0), xe_text + 1): out[y][x] = 0
    if a["xs"] is not None:
        for x in range(a["xs"], a["xe"] + 1): out[a["yl"]][x] = 0
        if a.get("dotted"):
            x = a["xe"]
            while x >= tx0 + w + 3: out[a["yl"]][x] = color; x -= a["dotted"]
        else:
            for x in range(tx0 + w + 3, a["xe"] + 1): out[a["yl"]][x] = color
    def put(x, y):
        if 0 <= x < W and 0 <= y < len(out): out[y][x] = color
    F.draw(ru, put, tx0, l["r0"])

def render(name, write=True):
    d, info, rows = G.load("Guide", name); out = [r[:] for r in rows]; W = len(rows[0]); rep = []
    spec = {}
    p = f"{ROOT}/text/gfx/Guide/{name}.lines.tsv"
    for ln in open(p, encoding="utf-8"):
        f = ln.rstrip("\n").split("\t")
        if len(f) >= 3 and f[0].isdigit() and f[2].strip(): spec[int(f[0])] = f[2].strip()
    for i, (l, a) in enumerate(lines_info(rows, ICON_PAGES.get(name, 0))):
        if i not in spec: continue
        ok, w, limit = fits(l, a, spec[i], W)
        rep.append((i, ok, w, limit, F.missing(spec[i])))
        draw_item(out, l, a, spec[i])
    if write and all(ok for _, ok, *_ in rep):
        nd, _, _ = ds_gfx.repack(d, info, out)
        path = f"{ROOT}/patched_raw/Guide/ue/{name}.pbg.z"; os.makedirs(os.path.dirname(path), exist_ok=True)
        open(path, "wb").write(lz10.compress(nd))
    return rep

if __name__ == "__main__":
    name = sys.argv[2]
    if "--skel" in sys.argv:
        for i, (l, a) in enumerate(skeleton(name)): print(i, "y", l["y0"], "tx0", a["tx0"], "leader", a["xs"], a["xe"], "num", a["num_x0"], "icon", a["icon_x1"])
    else:
        rep = render(name, write="--check" not in sys.argv)
        bad = [r for r in rep if not r[1]]
        print(name, "lines", len(rep), "BAD" if bad else "ok", [(i, f"{w}>{lim}" if not miss else f"missing {miss}") for i, ok, w, lim, miss in bad])
