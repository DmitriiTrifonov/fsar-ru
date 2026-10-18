"""Measure the dialogue text extent in a melonDS window screenshot (in DS pixels).
usage: measure_text.py shot.png   (top screen text box region of the 582x837 window @2x)"""
import sys
from PIL import Image
im = Image.open(sys.argv[1]).convert("L"); W, H = im.size
X0, X1 = 43, 1121; SCALE = (X1 - X0) / 256          # window -> DS pixels
# dialogue box: below the red separator, left of the portrait
box = (X0, 680, 905, 860)
px = im.load(); xs = []; ys = []
for y in range(box[1], box[3]):
    for x in range(box[0], box[2]):
        if px[x, y] < 70:
            xs.append(x); ys.append(y)
if not xs:
    print("no text found"); sys.exit()
print(f"text x: {(min(xs)-X0)/SCALE:.1f}..{(max(xs)-X0)/SCALE:.1f} DS px  (width {(max(xs)-min(xs))/SCALE:.1f}); "
      f"y: {(min(ys)-box[1])/SCALE:.1f}..{(max(ys)-box[1])/SCALE:.1f} rows={(max(ys)-min(ys))/SCALE:.1f} px tall; scale {SCALE:.3f}")
