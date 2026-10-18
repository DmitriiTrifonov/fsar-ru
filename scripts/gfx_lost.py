"""gfx_lost.py <page> --skel | --check | (render): LostList pages (dark antialiased text on a tan card: bg index 14, text index 1).
Blocks: heading (line with an underline row) or body lines (pitch 12; a line starting with a bullet dot starts a block).
text/gfx/LostList/<page>.tsv: id<TAB>EN<TAB>RU per block. Body: pixel font (gfx_font) in index 1; heading: main dialog font scaled, antialiased.
Body blocks may grow into the free space below them (up to the next ink or the card bottom)."""
import sys, os, collections
sys.path.insert(0, os.path.dirname(__file__))
import gfx_blocks as G, gfx_font as F, ds_gfx, lz10, fontio, pobj_edit as E
import numpy as np
from PIL import Image, ImageDraw

ROOT = G.ROOT; BG = 14; FG = 1; PITCH = 12; UL = 9
MAIN = None
# max compressed size per page = the 512-byte-aligned size in the ROM the savestates were taken on (gfx7..gfx10); growing past it shifts every later file
SLOT = {"lostSTR_r02": 10752}
# framed block printed upside down: (x0, y0, x1, y1) of the frame interior and the upright text lines (the first line is data, left as in the original)
# leftover English rows inside picture blocks: (y0, y1, x0, x1) wiped to the card colour
WIPE = {"lostSTR_r17": [(92, 104, 9, 200), (105, 106, 9, 80)]}   # 2nd line of the dog question ("dog must travel to reach his master?")
UPSIDE_DOWN = {"lostSTR_r07": (43, 145, 163, 182, ["???PASS ISLAND", "Впишите пропущенные", "буквы и отправьте…"])}

def interior(rows):
    set_colors(rows)
    ys = [y for y, r in enumerate(rows) if sum(1 for v in r if v == BG) > 200]
    xs = [x for x in range(256) if sum(1 for y in range(ys[0], ys[-1]) if rows[y][x] == BG) > 200]
    return xs[0] + 6, xs[-1] - 6, ys[0] + 1, ys[-1] - 2

PAL = None

def set_colors(rows, pal=None):
    """per-page card colour (most common index except 0); text colour = darkest used colour (not pure black)"""
    global BG, FG
    c = collections.Counter(v for r in rows for v in r if v)
    BG = c.most_common(1)[0][0]
    if pal is None: pal = PAL
    lum = lambda i: sum(pal[i]) if pal else i
    FG = min((i for i, n in c.items() if n >= 150 and i != BG and sum(pal[i]) > 30), key=lum) if pal else c.most_common(2)[1][0]

def max_run(r, x0, x1):
    best = run = 0; prev = None
    for x in range(x0, x1 + 1):
        v = r[x]
        if v == prev and v != BG: run += 1
        else: run = 1
        prev = v; best = max(best, run)
    return best

def analyse(rows):
    X0, X1, Y0, Y1 = interior(rows)
    corner = sum(1 for y in range(Y1 - 24, Y1 + 1) for x in range(234, X1 + 1) if rows[y][x] != BG)
    has_counter = corner >= 40           # page counter (1/3) bottom right is left alone
    XR = lambda y: 228 if (has_counter and y >= Y1 - 16) else X1
    cnt = {y: sum(1 for x in range(X0, XR(y) + 1) if rows[y][x] != BG) for y in range(Y0, Y1 + 1)}
    runs = []; y = Y0
    while y <= Y1:
        if cnt[y] > 2:
            a = y
            while y <= Y1 and cnt[y] > 2: y += 1
            runs.append((a, y - 1))
        else: y += 1
    merged = []
    for (a, b) in runs:     # a single underline row belongs to the heading above it
        if merged and max_run(rows[a], X0, X1) >= 20 and a - merged[-1][1] <= 3:
            merged[-1] = (merged[-1][0], a)
            if b - a >= 1:
                a += 1
                while a <= b and cnt[a] <= 2: a += 1
                if a <= b: merged.append((a, b))
        else: merged.append((a, b))
    runs = merged
    lines = []
    for (a, b) in runs:
        ul = [yy for yy in range(a, b + 1) if max_run(rows[yy], X0, X1) >= 20]
        xs = [x for yy in range(a, b + 1) for x in range(X0, XR(yy) + 1) if rows[yy][x] != BG]
        # split a run into body lines if it is taller than one line (pitch 12 with no blank rows)
        if ul:
            lines.append(dict(kind="h", y0=a, y1=b, ul=ul[0], x0=min(xs), x1=max(xs), text_y1=ul[0] - 2))
            continue
        n = max(1, round((b - a + 1 - 3) / PITCH))
        cuts = [a]
        for k in range(1, n):
            e = a + PITCH * k - 2
            cuts.append(min(range(e - 3, e + 4), key=lambda yy: (cnt.get(yy, 99), abs(yy - e))))
        for k, st in enumerate(cuts):
            en = cuts[k + 1] - 1 if k + 1 < len(cuts) else b
            xs2 = [x for yy in range(st, en + 1) for x in range(X0, XR(yy) + 1) if rows[yy][x] != BG]
            if not xs2: continue
            mx = max(cnt[yy] for yy in range(st, en + 1)); base = max(yy for yy in range(st, en + 1) if cnt[yy] >= 0.5 * mx)
            lines.append(dict(kind="b", y0=st, y1=en, x0=min(xs2), x1=max(xs2), base=base))
    return (X0, X1, Y0, Y1), lines

def has_bullet(rows, l):
    x = l["x0"]; ink = [(xx, yy) for yy in range(l["y0"], l["y1"] + 1) for xx in range(x, x + 5) if rows[yy][xx] != BG]
    cols = sorted({xx for xx, _ in ink}); tall = {yy for _, yy in ink}
    return bool(cols) and max(cols) - x <= 3 and len(tall) <= 5 and any(rows[l["y0"] + k][xx] != BG for k in range(l["y1"] - l["y0"] + 1) for xx in range(x + 4, x + 9))

def blocks(rows):
    bounds, lines = analyse(rows); out = []
    for l in lines:
        if l["kind"] == "h": out.append(dict(kind="h", lines=[l])); continue
        bl = has_bullet(rows, l)
        prev = out[-1] if out else None
        if prev and prev["kind"] == "b" and not bl and abs(l["base"] - prev["lines"][-1]["base"] - PITCH) <= 2: prev["lines"].append(l)
        else: out.append(dict(kind="b", bullet=bl, lines=[l]))
    for b in out:
        ls = b["lines"]; b["left"] = min(l["x0"] for l in ls); b["right"] = max(l["x1"] for l in ls)
        b["y0"] = ls[0]["y0"]; b["y1"] = ls[-1]["y1"]; b["n"] = len(ls)
    for k, b in enumerate(out):
        nxt = out[k + 1]["y0"] if k + 1 < len(out) else bounds[3] + 1
        b["room"] = nxt - b["y1"] - 1
    return bounds, out

def tsv_path(name): return f"{ROOT}/text/gfx/LostList/{name}.tsv"

def skeleton(name):
    d, info, rows = G.load("LostList", name); global PAL; PAL = info["pal"]; bounds, bl = blocks(rows)
    p = tsv_path(name); os.makedirs(os.path.dirname(p), exist_ok=True); old = {}
    if os.path.exists(p):
        for ln in open(p, encoding="utf-8"):
            f = ln.rstrip("\n").split("\t")
            if len(f) >= 3 and f[0].isdigit(): old[int(f[0])] = f[1:3]
    with open(p, "w", encoding="utf-8") as fo:
        for i, b in enumerate(bl): fo.write(f"{i}\t{old.get(i, ['', ''])[0]}\t{old.get(i, ['', ''])[1]}\n")
    pal = info["pal"]; os.makedirs(f"{ROOT}/dumps/gfx/skel", exist_ok=True)
    im = Image.new("RGB", (256, 384)); px = im.load()
    for y, r in enumerate(rows):
        for x, v in enumerate(r): px[x, y] = pal[v]
    big = im.resize((768, 1152), Image.NEAREST); dr = ImageDraw.Draw(big)
    for i, b in enumerate(bl):
        dr.rectangle([b["left"] * 3 - 3, b["y0"] * 3 - 3, b["right"] * 3 + 3, b["y1"] * 3 + 3], outline=(255, 0, 0)); dr.text((4, b["y0"] * 3), f"#{i}", fill=(0, 0, 255))
        ya, yb = max(0, b["y0"] - 4), min(384, b["y1"] + 5)
        im.crop((max(0, b["left"] - 4), ya, min(256, b["right"] + 5), yb)).resize(((min(256, b["right"] + 5) - max(0, b["left"] - 4)) * 4, (yb - ya) * 4), Image.NEAREST).save(f"{ROOT}/dumps/gfx/skel/LostList_{name}_b{i}.png")
    big.save(f"{ROOT}/dumps/gfx/skel/LostList_{name}.png")
    return bl, bounds

def wrap(text, first_w, w, font_w):
    if "//" in text:     # forced line breaks
        out = []; fw = first_w
        for part in text.split("//"):
            out += wrap(part.strip(), fw, w, font_w); fw = w
        return out
    words = text.split(); lines = []; cur = ""; lim = first_w
    for wd in words:
        t = (cur + " " + wd).strip()
        if font_w(t) <= lim or not cur: cur = t
        else: lines.append(cur); cur = wd; lim = w
    if cur: lines.append(cur)
    return lines

def head_cov(text, scale=1.0):
    global MAIN
    if MAIN is None: MAIN = fontio.Font(f"{ROOT}/patched_raw/Chapter/Pack/Common/font.nftr")
    cov, w = E.text_coverage(text, MAIN, bold=0, space=0)
    a = np.array(cov); h, ww = a.shape; sy = 0.95; sx = scale
    nh, nw = int(round(h * sy)), int(round(ww * sx)); out = np.zeros((nh, nw))
    for y in range(nh):
        for x in range(nw):
            y0 = y / sy; y1 = (y + 1) / sy; x0 = x / sx; x1 = (x + 1) / sx
            out[y, x] = a[int(y0):max(int(y0) + 1, int(np.ceil(y1))), int(x0):max(int(x0) + 1, int(np.ceil(x1)))].mean()
    return out

def render(name, write=True):
    d, info, rows = G.load("LostList", name); global PAL; PAL = info["pal"]; out = [r[:] for r in rows]; (X0, X1, Y0, Y1), bl = blocks(rows); pal = info["pal"]
    spec = {}
    if os.path.exists(tsv_path(name)):
        for ln in open(tsv_path(name), encoding="utf-8"):
            f = ln.rstrip("\n").split("\t")
            if len(f) >= 3 and f[0].isdigit() and f[2].strip(): spec[int(f[0])] = f[2].strip()
    # palette ramp from bg to fg
    bgc, fgc = pal[BG], pal[FG]
    def ramp(c):
        t = tuple(bgc[k] * (1 - c) + fgc[k] * c for k in range(3))
        return min(range(1, 16), key=lambda i: sum((pal[i][k] - t[k]) ** 2 for k in range(3))) if c > 0.08 else BG
    corner = sum(1 for y in range(Y1 - 24, Y1 + 1) for x in range(234, X1 + 1) if rows[y][x] != BG)
    XRL = lambda y1: 228 if (corner >= 40 and y1 >= Y1 - 16) else X1
    rep = []
    for i, b in enumerate(bl):
        if i not in spec: continue
        ru = spec[i]; miss = F.missing(ru.replace("№", "N")) if False else F.missing(ru)
        if b["kind"] == "h":
            l = b["lines"][0]; cov = head_cov(ru); w = cov.shape[1]; XRh = XRL(l["y1"])
            centred = abs((l["x0"] + l["x1"]) / 2 - (X0 + X1) / 2) <= 6
            xs0 = (X0 + X1 - w) // 2 if centred else l["x0"]
            limit = (X1 - X0) if centred else XRh - l["x0"]
            ok = w <= limit and not miss; rep.append((i, ok, w, limit, miss))
            for y in range(l["y0"], l["y1"] + 1):
                for x in range(X0 - 3, XRh + (1 if XRh < X1 else 6)): out[y][x] = BG
            ytop = l["ul"] - 2 - cov.shape[0] + 2
            for y in range(cov.shape[0]):
                for x in range(min(w, XRh - xs0)):
                    v = (cov[y, x] - 0.12) * 1.9
                    if v > 0.08 and 0 <= ytop + y < 384: out[ytop + y][xs0 + x] = ramp(min(1, v))
            for x in range(xs0, min(XRh, xs0 + w + 2) + 1): out[l["ul"]][x] = UL
            continue
        XRb = XRL(b["y1"])
        left = b["left"]; x_first = left + (6 if b.get("bullet") else 0); room_lines = (b["room"] + PITCH - 3) // PITCH if b["room"] > 0 else 0
        allowed = b["n"] + max(0, (b["room"] - 4) // PITCH)
        lines = wrap(ru, XRb - x_first, XRb - (left + (6 if b.get("bullet") else 0)), F.width)
        ok = len(lines) <= allowed and not miss and all(F.width(t) <= XRb - x_first for t in lines)
        rep.append((i, ok, len(lines), allowed, miss))
        for y in range(b["y0"], min(b["y1"] + 1 + max(0, b["room"]), Y1)):   # all free rows below the block too: descenders of the old text can hang past y1
            for x in range(left + (6 if b.get("bullet") else 0) - 3, XRL(y) + (2 if XRL(y) < X1 else 6)): out[y][x] = BG
        base0 = next((l["base"] for l in b["lines"] if l["y1"] - l["y0"] >= 3), b["lines"][0]["base"])   # a 1-2 row stray (tail of the heading underline) is not the first text line
        for k, t in enumerate(lines[:allowed]):
            def put(x, y):
                if 0 <= x < 256 and 0 <= y < 384: out[y][x] = FG
            F.draw(t, put, left + (6 if b.get("bullet") else 0), base0 - 7 + PITCH * k)
    for b in bl:      # leftover tops of the old heading letters (isolated dots) just above each heading: original ink that the redraw did not touch
        if b["kind"] != "h": continue
        for y in range(max(Y0, b["y0"] - 3), b["y0"]):
            for x in range(max(X0, b["left"] - 1), min(X1, b["right"] + 2) + 1):
                if rows[y][x] != BG and out[y][x] == rows[y][x]: out[y][x] = BG
    for y0, y1, x0, x1 in WIPE.get(name, []):
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1): out[y][x] = BG
    if name in UPSIDE_DOWN:      # framed text printed upside down: redraw the frame interior as upright text rotated by 180 degrees
        x0, y0, x1, y1, lines = UPSIDE_DOWN[name]; w, h = x1 - x0 + 1, y1 - y0 + 1
        tmp = [[False] * w for _ in range(h)]
        for k, t in enumerate(lines):
            def put(x, y, k=k):
                if 0 <= x < w and 0 <= y < h: tmp[y][x] = True
            F.draw(t, put, 3, 2 + PITCH * k)
        for y in range(h):
            for x in range(w): out[y0 + y][x0 + x] = FG if tmp[h - 1 - y][w - 1 - x] else BG
    if write and all(ok for _, ok, *_ in rep):
        nd, _, _ = ds_gfx.repack(d, info, out)
        path = f"{ROOT}/patched_raw/LostList/ue/{name}.pbg.z"; os.makedirs(os.path.dirname(path), exist_ok=True)
        z = lz10.compress(nd)
        if len(z) > SLOT.get(name, 1 << 30): z = lz10.compress_opt(nd)   # keep the file inside its ROM slot: savestates keep the file table of the ROM they were taken on
        open(path, "wb").write(z)
    return rep

if __name__ == "__main__":
    name = sys.argv[1]
    if "--skel" in sys.argv:
        bl, bounds = skeleton(name); print("interior", bounds)
        for i, b in enumerate(bl): print(f"#{i}: {b['kind']} lines={b['n'] if 'n' in b else 1} left={b['left']} right={b['right']} y={b['y0']}-{b['y1']} room={b['room']}" + (" bullet" if b.get("bullet") else ""))
    else:
        rep = render(name, write="--check" not in sys.argv); bad = [r for r in rep if not r[1]]
        print(name, "blocks", len(rep), "BAD" if bad else "ok", [(i, f"{a}/{n}" if not miss else f"missing {miss}") for i, ok, a, n, miss in bad])
