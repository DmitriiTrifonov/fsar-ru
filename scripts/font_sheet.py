"""Render an NFTR font (3bpp/2bpp/1bpp bit-packed glyph cells) to a PNG contact sheet."""
import sys
sys.path.insert(0, __import__("os").path.dirname(__file__))
import nftr
from PIL import Image

path, out = sys.argv[1], sys.argv[2]
d = open(path, "rb").read(); o = nftr.parse(d); g = o["cglp"]
cw, ch, bpp, cell = g["cell_w"], g["cell_h"], g["depth"], g["cell_bytes"]
inv = {v: k for k, v in o["map"].items()}
cols = 16; rows = (g["glyphs"] + cols - 1) // cols; S = 4
img = Image.new("RGB", (cols * (cw + 2) * S, rows * (ch + 2) * S), (40, 40, 60))
px = img.load()
for gi in range(g["glyphs"]):
    base = g["data_off"] + gi * cell
    bits = int.from_bytes(d[base:base + cell], "big"); total = cell * 8
    for y in range(ch):
        for x in range(cw):
            k = y * cw + x
            v = (bits >> (total - bpp * (k + 1))) & ((1 << bpp) - 1)
            c = int(255 * v / ((1 << bpp) - 1))
            ox = (gi % cols) * (cw + 2) * S + x * S; oy = (gi // cols) * (ch + 2) * S + y * S
            for dy in range(S):
                for dx in range(S):
                    px[ox + dx, oy + dy] = (c, c, c)
img.save(out); print(out, img.size, "glyphs", g["glyphs"])
