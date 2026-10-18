import sys, pathlib, time
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import lz10
src = pathlib.Path("extracted/data")
n = same = smaller = bad = 0; osz = nsz = 0; t = time.time()
for f in src.rglob("*.z"):
    if not f.name.endswith((".s.z", ".txt.z")):
        continue
    orig = f.read_bytes(); raw = lz10.decompress(orig)
    new = lz10.compress(raw)
    n += 1; osz += len(orig); nsz += len(new)
    if lz10.decompress(new) != raw: bad += 1
    same += new == orig; smaller += len(new) <= len(orig)
print(f"files {n}, roundtrip bad {bad}, byte-identical {same}, not larger {smaller}, size orig {osz} new {nsz}, {time.time()-t:.0f}s")
