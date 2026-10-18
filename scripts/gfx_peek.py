"""gfx_peek.py Guide <page> <y0> <y1> <out.png> [scale]: crop of the patched page (patched_raw) rendered with the real palette."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import gfx_frames as FR, ds_gfx
from PIL import Image
page, y0, y1, out = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]; sc = int(sys.argv[5]) if len(sys.argv) > 5 else 3
d, info, rows = FR.load_base(page)
im = ds_gfx.render_screen(d, info) if hasattr(ds_gfx, "render_screen") else None
im = im.convert("RGB").crop((0, y0, 256, y1)); im.resize((256 * sc, (y1 - y0) * sc), Image.NEAREST).save(out)
