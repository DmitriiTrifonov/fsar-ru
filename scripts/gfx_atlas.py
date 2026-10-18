"""Build a glyph atlas from the text pages: cut lines (pitch 11) into glyph bitmaps by empty columns, cluster identical ones.
usage: gfx_atlas.py <out_dir> <dir with .pbg> [more dirs...]"""
import sys, os, glob, collections
sys.path.insert(0, os.path.dirname(__file__))
import ds_gfx
from PIL import Image

PITCH = 11


def page_rows(path):
    d = open(path, "rb").read(); info = ds_gfx.parse(d)
    rows = ds_gfx.decode_indexed(d, info)
    return [[1 if v else 0 for v in r] for r in rows]


def line_bands(img):
    """Row bands that contain ink (separated by empty rows); tall bands are cut into PITCH-high lines."""
    H = len(img); bands = []; r = 0
    while r < H:
        if any(img[r]):
            s = r
            while r < H and any(img[r]):
                r += 1
            bands.append((s, r))
        else:
            r += 1
    lines = []
    for s, e in bands:
        y = s
        while y < e:
            lines.append(y); y += PITCH
    return lines


def tokens(img, y0):
    W = len(img[0]); H = len(img)
    rows = [img[y] if 0 <= y < H else [0] * W for y in range(y0, y0 + PITCH)]
    cols = [any(rows[y][x] for y in range(PITCH)) for x in range(W)]
    out = []; x = 0
    while x < W:
        if cols[x]:
            s = x
            while x < W and cols[x]:
                x += 1
            bm = tuple(tuple(rows[y][s:x]) for y in range(PITCH))
            out.append((s, x, bm))
        else:
            x += 1
    return out


if __name__ == "__main__":
    out = sys.argv[1]; os.makedirs(out, exist_ok=True)
    counts = collections.Counter(); example = {}
    pages = 0
    for d in sys.argv[2:]:
        for f in sorted(glob.glob(f"{d}/*.pbg")):
            img = page_rows(f); pages += 1
            for y0 in line_bands(img):
                for s, e, bm in tokens(img, y0):
                    counts[bm] += 1; example.setdefault(bm, (os.path.basename(f), y0, s))
    print(pages, "pages;", sum(counts.values()), "tokens;", len(counts), "distinct bitmaps")
    ranked = counts.most_common()
    # atlas image: 12 per row, 4x scale, with index
    S = 5; cols = 14; cw = 16; ch = (PITCH + 3)
    rows_n = (len(ranked) + cols - 1) // cols
    atlas = Image.new("RGB", (cols * cw * S, rows_n * ch * S), (40, 0, 40)); px = atlas.load()
    for i, (bm, n) in enumerate(ranked):
        ox, oy = (i % cols) * cw * S, (i // cols) * ch * S
        for y, row in enumerate(bm):
            for x, v in enumerate(row):
                if v and x < cw - 1:
                    for dy in range(S):
                        for dx in range(S):
                            px[ox + x * S + dx, oy + y * S + dy] = (255, 255, 255)
    atlas.save(f"{out}/atlas.png")
    import pickle
    pickle.dump(ranked, open(f"{out}/atlas.pkl", "wb"))
    print("saved", f"{out}/atlas.png", atlas.size)
