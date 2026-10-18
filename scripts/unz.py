import sys, pathlib, collections
sys.path.insert(0, str(pathlib.Path(__file__).parent))
import lz10
src = pathlib.Path("extracted/data"); dst = pathlib.Path("decoded")
stats = collections.Counter(); bad = []
for f in src.rglob("*.z"):
    d = f.read_bytes()
    try:
        out = lz10.decompress(d)
    except Exception as e:
        bad.append((str(f), repr(e))); continue
    o = dst / f.relative_to(src).with_suffix("")
    o.parent.mkdir(parents=True, exist_ok=True); o.write_bytes(out)
    stats[o.suffix] += 1
print(stats.most_common(15)); print("bad", len(bad), bad[:5])
