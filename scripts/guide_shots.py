"""guide_shots.py <page> : prints an emu_script macro that opens Guide page <page> from states/guide-grid.ml3 and shoots the bottom screen while scrolling.
stitch: guide_shots.py --stitch <page>  -> dumps/emu/guide/pNN.png (bottom screens one under another)"""
import sys, glob, os
from PIL import Image
if sys.argv[1] == "--stitch":
    n = int(sys.argv[2]); fs = sorted(glob.glob(f"dumps/emu/guide/q{n:02d}_*.png"))
    ims = [Image.open(f) for f in fs]; ims = [i.crop((0, i.height // 2, i.width, i.height)) for i in ims]
    W = ims[0].width; H = ims[0].height
    out = Image.new("RGB", (W * 2, H * ((len(ims) + 1) // 2)))
    for k, im in enumerate(ims): out.paste(im, ((k % 2) * W, (k // 2) * H))
    out.save(f"dumps/emu/guide/q{n:02d}.png"); print(out.size)
