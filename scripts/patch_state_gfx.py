"""patch_state_gfx.py <state.ml1> <out.ml1> <orig.pobj> <new.pobj[.z]>: write the new 4bpp tile block of a .pobj over every copy of it
found in a savestate (RAM copy and VRAM), so an old savestate shows freshly patched sprites without replaying the game.
Copies are located through tiles that are identical in the original and new files."""
import sys, os, collections
sys.path.insert(0, os.path.dirname(__file__))
import ds_gfx, lz10

def ncgr(d):
    i = ds_gfx.parse(d); return d[i["tile_off"]:i["tile_off"] + i["tile_size"]]

if __name__ == "__main__":
    st, out, old, new = sys.argv[1:5]
    od = open(old, "rb").read(); nd = open(new, "rb").read()
    if old.endswith(".z"): od = lz10.decompress(od)
    if new.endswith(".z"): nd = lz10.decompress(nd)
    a, b = ncgr(od), ncgr(nd); assert len(a) == len(b)
    s = bytearray(open(st, "rb").read()); votes = collections.Counter()
    for t in range(0, len(a), 32):
        tile = a[t:t + 32]
        if tile != b[t:t + 32] or len(set(tile)) < 6: continue
        pos = s.find(tile)
        n = 0
        while pos >= 0 and n < 6:
            votes[pos - t] += 1; n += 1; pos = s.find(tile, pos + 1)
    bases = [k for k, v in votes.items() if v >= 40]
    for base in bases:
        s[base:base + len(b)] = b
    tiles = 0
    if not bases:    # only part of the image is resident (e.g. the visible window of a long page): replace changed tiles one by one
        for t in range(0, len(a), 32):
            ot, nt = bytes(a[t:t + 32]), bytes(b[t:t + 32])
            if ot == nt or len(set(ot)) < 5: continue
            pos = s.find(ot)
            while pos >= 0:
                s[pos:pos + 32] = nt; tiles += 1; pos = s.find(ot, pos + 32)
    open(out, "wb").write(s); print("copies patched at", [hex(x) for x in bases], "tiles replaced", tiles, "top votes", votes.most_common(4))
