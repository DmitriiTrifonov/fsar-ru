import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import ds_gfx, lz10, gfx_blocks as G
from PIL import Image
ROOT = G.ROOT
def img(path, c=(0, 50, 256, 340)):
    d = lz10.decompress(open(path, "rb").read()); i = ds_gfx.parse(d); rows = ds_gfx.decode_indexed(d, i); pal = i["pal"]
    im = Image.new("RGB", (256, 384))
    for y, r in enumerate(rows):
        for x, v in enumerate(r): im.putpixel((x, y), pal[v])
    return im.crop(c)
names = sys.argv[1:]
os.makedirs(f"{ROOT}/dumps/gfx/lost_ru", exist_ok=True)
for n in names:
    a = img(f"{ROOT}/extracted/data/LostList/ue/{n}.pbg.z"); b = img(f"{ROOT}/patched_raw/LostList/ue/{n}.pbg.z")
    o = Image.new("RGB", (516, a.height)); o.paste(a, (0, 0)); o.paste(b, (260, 0)); o.resize((o.width * 2, o.height * 2), Image.NEAREST).save(f"{ROOT}/dumps/gfx/lost_ru/{n}.png")
