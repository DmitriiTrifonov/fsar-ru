"""gfx_extract.py Guide <page> [--write]: block skeleton text/gfx/Guide/<page>.tsv (id, r0, nlines, left, right, indent, bullet, EN, RU).
A block = consecutive lines with pitch <= 12 px. r0 = row of the first line's cap top (x-height top - 2)."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import gfx_blocks as G

def line_color(rows, l):
    import collections
    c = collections.Counter(v for y in range(l["y0"], l["y1"] + 1) for v in rows[y] if v)
    return c.most_common(1)[0][0] if c else 2

def blocks(rows):
    L = G.lines_of(rows); out = []
    for l in L: l["color"] = line_color(rows, l)
    for l in L:
        if out and l["y0"] - out[-1][-1]["y0"] <= 13 and abs(l["base"] - out[-1][-1]["base"] - 11) <= 2 and l["color"] == out[-1][-1]["color"]: out[-1].append(l)
        else: out.append([l])
    res = []
    for b in out:
        left = min(l["x0"] for l in b); right = max(l["x1"] for l in b)
        first = b[0]; r0 = first["base"] - 2
        bullet = int(is_bullet(rows, first))
        indent = first["x0"] - left
        res.append(dict(color=first["color"], r0=r0, n=len(b), left=left, right=right, indent=indent, bullet=bullet, y0=b[0]["y0"], y1=b[-1]["y1"], lines=b))
    return res

def is_bullet(rows, l):
    """solid 5x5 square within the first columns of the line"""
    for x in range(l["x0"], l["x0"] + 4):
        for y in range(l["y0"], l["y0"] + 6):
            if all(rows[y + j][x + i] for i in range(5) for j in range(5) if y + j < len(rows)): return True
    return False

def skeleton(kind, name):
    """TSV skeleton text/gfx/<kind>/<name>.tsv (existing translations are kept) + overlay PNG with block ids at 2x in dumps/gfx/skel/."""
    from PIL import Image, ImageDraw
    d, info, rows = G.load(kind, name); bl = blocks(rows)
    path = f"{G.ROOT}/text/gfx/{kind}/{name}.tsv"; os.makedirs(os.path.dirname(path), exist_ok=True)
    old = {}
    if os.path.exists(path):
        for ln in open(path, encoding="utf-8"):
            f = ln.rstrip("\n").split("\t")
            if len(f) >= 3 and f[0].isdigit(): old[int(f[0])] = f[1:3]
    with open(path, "w", encoding="utf-8") as fo:
        for i, b in enumerate(bl):
            en, ru = old.get(i, ["", ""])
            fo.write(f"{i}\t{en}\t{ru}\n")
    W = len(rows[0]); y0 = max(0, bl[0]["y0"] - 12) if bl else 0; y1 = min(len(rows), bl[-1]["y1"] + 12) if bl else 1
    im = Image.new("RGB", (W * 2 + 40, (y1 - y0) * 2), (40, 40, 60)); px = im.load()
    for y in range(y0, y1):
        for x in range(W):
            if rows[y][x]:
                for dy in range(2):
                    for dx in range(2): px[x * 2 + dx, (y - y0) * 2 + dy] = (255, 255, 255)
    dr = ImageDraw.Draw(im)
    for i, b in enumerate(bl):
        dr.rectangle([b["left"] * 2 - 2, (b["y0"] - y0) * 2 - 2, b["right"] * 2 + 2, (b["y1"] - y0) * 2 + 2], outline=(255, 80, 80))
        dr.text((W * 2 + 4, (b["y0"] - y0) * 2), f"#{i}", fill=(255, 255, 0))
    os.makedirs(f"{G.ROOT}/dumps/gfx/skel", exist_ok=True); im.save(f"{G.ROOT}/dumps/gfx/skel/{kind}_{name}.png")
    for i, b in enumerate(bl):   # 3x crop of every block for reading
        ya, yb = max(0, b["y0"] - 3), min(len(rows), b["y1"] + 4); xa, xb = max(0, b["left"] - 3), min(W, b["right"] + 4)
        c = Image.new("RGB", ((xb - xa) * 3, (yb - ya) * 3), (0, 0, 0)); cp = c.load()
        for y in range(ya, yb):
            for x in range(xa, xb):
                v = rows[y][x]
                if v:
                    col = (255, 255, 255) if v == 2 else (120, 200, 255)
                    for dy in range(3):
                        for dx in range(3): cp[(x - xa) * 3 + dx, (y - ya) * 3 + dy] = col
        c.save(f"{G.ROOT}/dumps/gfx/skel/{kind}_{name}_b{i}.png")
    return bl

if __name__ == "__main__":
    kind, name = sys.argv[1], sys.argv[2]
    if "--skel" in sys.argv:
        for i, b in enumerate(skeleton(kind, name)):
            budget = int(b["n"] * (b["right"] - b["left"]) / 4.8)
            print(f"#{i}: lines={b['n']} width={b['right']-b['left']}px bullet={b['bullet']} indent={b['indent']} budget~{budget} chars")
        sys.exit()
    d, info, rows = G.load(kind, name)
    for i, b in enumerate(blocks(rows)):
        print(i, {k: v for k, v in b.items() if k != "lines"})
