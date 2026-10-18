"""Export .pbg backgrounds to PNG (full colour) and build contact sheets.
usage: gfx_export.py <decoded dir with .pbg> <out dir>   e.g. decoded/2D/ue dumps/gfx/2D_ue"""
import sys, os, glob
sys.path.insert(0, os.path.dirname(__file__))
import ds_gfx
from PIL import Image, ImageDraw

src, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
items = []
for f in sorted(glob.glob(f"{src}/*.pbg")):
    d = open(f, "rb").read(); info = ds_gfx.parse(d)
    if "pal" not in info:
        info["pal"] = [(i, i, i) for i in range(256)]
    im = ds_gfx.render_screen(d, info)
    name = os.path.basename(f)[:-4]
    im.save(f"{out}/{name}.png"); items.append((name, im))
print(len(items), "images ->", out)
# contact sheets: 4 per row, thumbnails scaled to 50 %, tall images cut into 192-px screens
THUMB_W, GAP, COLS, PER = 128, 8, 6, 24
for s in range(0, len(items), PER):
    chunk = items[s:s + PER]; cells = []
    for name, im in chunk:
        th = im.resize((THUMB_W, max(1, im.height // 2)), Image.LANCZOS)
        cells.append((name, th))
    rows = [cells[i:i + COLS] for i in range(0, len(cells), COLS)]
    heights = [max(c[1].height for c in r) + 14 for r in rows]
    sheet = Image.new("RGB", (COLS * (THUMB_W + GAP), sum(heights)), (50, 0, 50)); dr = ImageDraw.Draw(sheet); y = 0
    for r, h in zip(rows, heights):
        for k, (name, th) in enumerate(r):
            x = k * (THUMB_W + GAP); sheet.paste(th, (x, y + 12)); dr.text((x, y), name[:20], fill=(255, 255, 255))
        y += h
    sheet.save(f"{out}/_sheet{s // PER + 1}.png")
