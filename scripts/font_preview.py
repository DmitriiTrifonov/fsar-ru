"""Render sample lines with an NFTR font (uses cmap + advance widths): font_preview.py FONT OUT.png"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import fontio
from PIL import Image

f = fontio.Font(sys.argv[1]); out = sys.argv[2]; S = 5
LINES = ["I'm Sumio Mondo. Hello, world 0123",
         "АБВГДЕЁЖЗИЙКЛМНОП",
         "РСТУФХЦЧШЩЪЫЬЭЮЯ",
         "абвгдеёжзийклмноп",
         "рстуфхцчшщъыьэюя",
         "Я Сумио Мондо. Я ищу вещи.",
         "Съешь ещё этих мягких",
         "французских булок, да выпей чаю!"]
H = f.h + 3
img = Image.new("L", (240 * S, (len(LINES) * H + 2) * S), 30)
px = img.load()
for li, line in enumerate(LINES):
    x0 = 2
    for ch in line:
        gi = f.map.get(ord(ch))
        if gi is None:
            x0 += 6; continue
        g = f.glyph(gi); lw, gw, adv = f.width(gi)
        for y in range(f.h):
            for x in range(f.w):
                v = g[y][x]
                if v:
                    c = 30 + int((225) * v / ((1 << f.bpp) - 1))
                    for dy in range(S):
                        for dx in range(S):
                            px[(x0 + x) * S + dx, (li * H + y + 1) * S + dy] = c
        x0 += adv
img.save(out); print(out, img.size)
