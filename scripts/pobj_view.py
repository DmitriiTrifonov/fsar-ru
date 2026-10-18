"""Render the cells (OBJ sprites) of a .pobj: pobj_view.py <file.pobj> <out.png>
NCER 'CEBK' -> cells -> OAM entries (attr0/1/2); tiles are read in 1D order from the NCGR, palette bank from attr2."""
import struct, sys, os
sys.path.insert(0, os.path.dirname(__file__))
import ds_gfx
from PIL import Image, ImageDraw

SIZES = {(0, 0): (8, 8), (0, 1): (16, 16), (0, 2): (32, 32), (0, 3): (64, 64),
         (1, 0): (16, 8), (1, 1): (32, 8), (1, 2): (32, 16), (1, 3): (64, 32),
         (2, 0): (8, 16), (2, 1): (8, 32), (2, 2): (16, 32), (2, 3): (32, 64)}


def cells(d, info):
    pos = [p for m, p, s in info["sections"] if m == "RECN"][0]
    blk = pos + 16
    cnt, attr, off, mapmode = struct.unpack_from("<HHII", d, blk + 8)
    base = blk + 8 + off; ext = attr & 1; step = 16 if ext else 8
    out = []
    for i in range(cnt):
        n, cattr, ooff = struct.unpack_from("<HHI", d, base + i * step)
        oams = []
        oam_base = base + cnt * step + ooff
        for k in range(n):
            a0, a1, a2 = struct.unpack_from("<HHH", d, oam_base + 6 * k)
            y = a0 & 0xFF; y = y - 256 if y >= 128 else y
            x = a1 & 0x1FF; x = x - 512 if x >= 256 else x
            shape = a0 >> 14; size = a1 >> 14; w, h = SIZES[(shape, size)]
            oams.append(dict(x=x, y=y, w=w, h=h, hf=(a1 >> 12) & 1, vf=(a1 >> 13) & 1, tile=a2 & 0x3FF, bank=a2 >> 12, bpp8=(a0 >> 13) & 1))
        out.append(oams)
    return out, mapmode


def render(d, info, oams, mapshift):
    tiles = ds_gfx.tile_pixels(d, info); pal = info["pal"]
    if not oams: return Image.new("RGBA", (8, 8))
    x0 = min(o["x"] for o in oams); y0 = min(o["y"] for o in oams); x1 = max(o["x"] + o["w"] for o in oams); y1 = max(o["y"] + o["h"] for o in oams)
    img = Image.new("RGBA", (x1 - x0, y1 - y0), (0, 0, 0, 0)); px = img.load()
    for o in reversed(oams):
        t = o["tile"] << mapshift
        for ty in range(o["h"] // 8):
            for tx in range(o["w"] // 8):
                idx = t + ty * (o["w"] // 8) + tx
                if idx >= len(tiles): continue
                for y in range(8):
                    for x in range(8):
                        c = tiles[idx][y * 8 + x]
                        if c == 0: continue
                        X = tx * 8 + x; Y = ty * 8 + y
                        if o["hf"]: X = o["w"] - 1 - X
                        if o["vf"]: Y = o["h"] - 1 - Y
                        col = pal[o["bank"] * 16 + c] if o["bank"] * 16 + c < len(pal) else (255, 0, 255)
                        px[o["x"] - x0 + X, o["y"] - y0 + Y] = col + (255,)
    return img


if __name__ == "__main__":
    d = open(sys.argv[1], "rb").read(); info = ds_gfx.parse(d); cl, mm = cells(d, info)
    ims = [render(d, info, c, mm) for c in cl]
    W = 520; x = y = 0; rowh = 0; layout = []
    for i, im in enumerate(ims):
        s = 2; w, h = im.width * s, im.height * s
        if x + w + 6 > W: x = 0; y += rowh + 14; rowh = 0
        layout.append((x, y, i)); x += w + 6; rowh = max(rowh, h)
    sheet = Image.new("RGB", (W, y + rowh + 14), (60, 60, 90)); dr = ImageDraw.Draw(sheet)
    for (xx, yy, i), im in zip(layout, ims):
        sheet.paste(im.resize((im.width * 2, im.height * 2), Image.NEAREST), (xx, yy + 10), im.resize((im.width * 2, im.height * 2), Image.NEAREST))
        dr.text((xx, yy), str(i), fill=(255, 255, 0))
    sheet.save(sys.argv[2]); print(len(ims), "cells ->", sys.argv[2])
