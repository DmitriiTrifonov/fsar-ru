"""gfx_render_all.py: render every translated Guide page into patched_raw/Guide/ue (lines mode if <page>.lines.tsv exists, else blocks)."""
import sys, os, glob
sys.path.insert(0, os.path.dirname(__file__))
import gfx_render as R, gfx_lines as L, gfx_frames as FR, gfx_boxes as BX
ROOT = R.ROOT
names = sorted({os.path.basename(f).split(".")[0] for f in glob.glob(f"{ROOT}/text/gfx/Guide/*.tsv")})
def has(nm, kind): return os.path.exists(f"{ROOT}/text/gfx/Guide/{nm}.{kind}.tsv")
bad = 0
for nm in names:
    if has(nm, "lines"):
        rep = L.render(nm); kind = "lines"
    elif os.path.exists(f"{ROOT}/text/gfx/Guide/{nm}.tsv"):
        rep = R.render("Guide", nm); kind = "blocks"
    else: rep = []; kind = "frames-only"
    if has(nm, "frames"):
        rep = rep + FR.render(nm); kind += "+frames"
    if has(nm, "boxes"):
        rep = rep + BX.render(nm); kind += "+boxes"
    b = [r for r in rep if not r[1]]; bad += bool(b)
    print(nm, kind, len(rep), "BAD %s" % [(r[0]) for r in b] if b else "ok")
print("pages", len(names), "bad", bad)
