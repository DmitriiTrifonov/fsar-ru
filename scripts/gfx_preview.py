"""gfx_preview.py Guide <n>...: PNG of patched pages (patched_raw/Guide/ue) next to the original, cropped to the text area -> dumps/gfx/guide_ru/."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import ds_gfx, lz10, gfx_blocks as G
from PIL import Image
os.makedirs(f"{G.ROOT}/dumps/gfx/guide_ru", exist_ok=True)
def img(rows, y0, y1):
    im = Image.new("RGB", (256, y1 - y0), (200, 30, 30))
    for y in range(y0, y1):
        for x in range(256):
            v = rows[y][x]
            if v: im.putpixel((x, y - y0), (255, 255, 255) if v == 2 else (120, 200, 255))
    return im
for n in sys.argv[2:]:
    name = f"m_guide{int(n):02d}"
    d, info, rows = G.load("Guide", name)
    nd = lz10.decompress(open(f"{G.ROOT}/patched_raw/Guide/ue/{name}.pbg.z", "rb").read()); nr = ds_gfx.decode_indexed(nd, ds_gfx.parse(nd))
    ys = [y for y, r in enumerate(rows) if any(r)] or [0]; y0, y1 = max(0, ys[0] - 4), min(len(rows), ys[-1] + 6)
    a, b = img(rows, y0, y1), img(nr, y0, y1)
    o = Image.new("RGB", (516, y1 - y0)); o.paste(a, (0, 0)); o.paste(b, (260, 0))
    o.resize((o.width * 2, o.height * 2), Image.NEAREST).save(f"{G.ROOT}/dumps/gfx/guide_ru/{name}.png")
