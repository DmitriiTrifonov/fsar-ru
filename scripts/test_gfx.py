"""Round-trip tests for ds_gfx: decode -> repack without edits must be byte-identical for every .pbg;
a synthetic edit must decode back to the edited image."""
import sys, os, glob
sys.path.insert(0, os.path.dirname(__file__))
import ds_gfx

files = sorted(glob.glob("decoded/**/*.pbg", recursive=True))
bad = []
for f in files:
    d = open(f, "rb").read(); info = ds_gfx.parse(d)
    rows = ds_gfx.decode_indexed(d, info)
    out, changed, newt = ds_gfx.repack(d, info, rows)
    if out != d or changed or newt:
        bad.append((f, changed, newt, out == d))
print(f"no-edit round trip: {len(files)} files, not identical: {len(bad)}", bad[:5])

# synthetic edit: paint a block with an existing colour index and check decode == edited
import random
random.seed(1); errs = 0; grew = 0; tested = 0
for f in random.sample(files, 40):
    d = open(f, "rb").read(); info = ds_gfx.parse(d)
    rows = ds_gfx.decode_indexed(d, info)
    W, H = info["scr_w"], info["scr_h"]
    # draw a diagonal line (new tile patterns) using indices that exist in the picture
    idxs = sorted({v for r in rows for v in r})
    if len(idxs) < 2:
        continue
    for k in range(min(W, H, 64)):
        rows[20 + k // 2][16 + k] = idxs[-1] if info["bpp"] == 8 else (rows[20 + k // 2][16 + k] & ~15) | (idxs[-1] & 15)
    try:
        out, changed, newt = ds_gfx.repack(d, info, rows)
    except ValueError as e:
        print("skip", os.path.basename(f), e); continue
    tested += 1
    info2 = ds_gfx.parse(out)
    back = ds_gfx.decode_indexed(out, info2)
    if back != rows:
        errs += 1; print("MISMATCH", f)
    grew += newt > 0
print(f"edit test: {tested} files, mismatches {errs}, files that needed new tiles {grew}")
