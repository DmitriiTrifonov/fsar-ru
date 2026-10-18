"""walk_sheets.py <walk-dir> <prefix> [--cols 4] [--rows 15] [--full]: contact sheets from the screenshots of the `walk` macro command.
Default: only the dialogue window strip of the top screen (y 138..192), 4 x 15 = 60 lines per sheet -> <walk-dir>/sheet_<prefix>_<k>.png"""
import sys, glob, os
from PIL import Image, ImageDraw
d, prefix = sys.argv[1], sys.argv[2]
cols = int(sys.argv[sys.argv.index("--cols") + 1]) if "--cols" in sys.argv else 4
rows = int(sys.argv[sys.argv.index("--rows") + 1]) if "--rows" in sys.argv else 15
full = "--full" in sys.argv
fs = sorted(glob.glob(f"{d}/{prefix}_[0-9][0-9][0-9]*.png"))
box = (0, 0, 256, 192) if full else (0, 138, 256, 192); w, h = box[2] - box[0], box[3] - box[1]
per = cols * rows
for k in range(0, len(fs), per):
    W = Image.new("RGB", (w * cols, h * rows), (40, 40, 40)); dr = ImageDraw.Draw(W)
    for i, f in enumerate(fs[k:k + per]):
        W.paste(Image.open(f).convert("RGB").crop(box), ((i % cols) * w, (i // cols) * h)); dr.text(((i % cols) * w + 2, (i // cols) * h + 1), str(k + i), fill=(255, 255, 0))
    out = f"{d}/sheet_{prefix}_{k // per}.png"; W.save(out); print(out, W.size)
