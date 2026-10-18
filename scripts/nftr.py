"""Minimal NFTR (Nitro font) reader: prints structure and covered code points."""
import struct, sys


def parse(d):
    assert d[:4] == b"RTFN", "not NFTR"
    ver, fsize, hsize, nblocks = struct.unpack_from("<HIHH", d, 6)
    pos = hsize; blocks = {}
    for _ in range(nblocks):
        tag = d[pos:pos + 4].decode("ascii"); size = struct.unpack_from("<I", d, pos + 4)[0]
        blocks[tag] = (pos, size); pos += size
    out = {"version": hex(ver), "blocks": {k: v for k, v in blocks.items()}}
    p = blocks["FNIF"][0]
    (_, _, unk, lh, defidx, dw, dl, dc, enc, off_glp, off_wdh, off_map) = struct.unpack_from("<4sIBBHBBBBIII", d, p)[0:12] if False else (None,)*12
    # FINF: tag,size, u8 unk, u8 lineheight, u16 defaultglyph, u8 defwidth(left), u8 def(glyph w), u8 def(adv), u8 enc, u32 cglp, u32 cwdh, u32 cmap
    unk, lh, defglyph, w_l, w_g, w_a, enc, o_glp, o_wdh, o_map = struct.unpack_from("<BBHbBBBIII", d, p + 8)
    out["finf"] = dict(lineheight=lh, default_glyph=defglyph, default_width=(w_l, w_g, w_a), encoding={0: "utf8", 1: "utf16", 2: "sjis", 3: "cp1252"}.get(enc, enc))
    g = blocks["PLGC"][0]
    cw, ch, cs, base, dw_, dh_, depth, rot = struct.unpack_from("<BBHbbBbB", d, g + 8)[:8] if False else struct.unpack_from("<BBHBBBB", d, g + 8)[:7] + (0,)
    sz = struct.unpack_from("<I", d, g + 4)[0]
    cw, ch, cellsz, baseline, maxw, depth, rot = struct.unpack_from("<BBHBBBB", d, g + 8)
    nglyph = (sz - 0x10) // cellsz
    out["cglp"] = dict(cell_w=cw, cell_h=ch, cell_bytes=cellsz, baseline=baseline, max_w=maxw, depth=depth, rotation=rot, glyphs=nglyph, data_off=g + 16)
    # CWDH
    w = blocks["HDWC"][0]
    first, last, nxt = struct.unpack_from("<HHI", d, w + 8)
    out["cwdh"] = dict(first=first, last=last, off=w + 16)
    widths = [struct.unpack_from("<bBB", d, w + 16 + 3 * i) for i in range(last - first + 1)]
    out["widths"] = widths
    # CMAP
    cm = []; off = o_map - 8
    while off:
        b = off
        lo, hi, typ, nxt = struct.unpack_from("<HHHxxI", d, b + 8)
        cm.append((lo, hi, typ))
        pairs = {}
        if typ == 0:
            idx0 = struct.unpack_from("<H", d, b + 20)[0]
            for c in range(lo, hi + 1): pairs[c] = idx0 + c - lo
        elif typ == 1:
            for c in range(lo, hi + 1):
                v = struct.unpack_from("<H", d, b + 20 + 2 * (c - lo))[0]
                if v != 0xFFFF: pairs[c] = v
        elif typ == 2:
            n = struct.unpack_from("<H", d, b + 20)[0]
            for i in range(n):
                c, gi = struct.unpack_from("<HH", d, b + 22 + 4 * i); pairs[c] = gi
        out.setdefault("map", {}).update(pairs)
        off = nxt - 8 if nxt else 0
    out["cmap_sections"] = cm
    return out


def ranges(codes):
    codes = sorted(codes); r = []
    for c in codes:
        if r and c == r[-1][1] + 1: r[-1][1] = c
        else: r.append([c, c])
    return r


if __name__ == "__main__":
    for path in sys.argv[1:]:
        o = parse(open(path, "rb").read())
        print("==", path); print(" finf", o["finf"]); print(" cglp", o["cglp"]); print(" cwdh", o["cwdh"], "width entries", len(o["widths"]))
        print(" cmap sections", o["cmap_sections"])
        rs = ranges(o["map"].keys()); print(" code point ranges:", " ".join(f"{a:04X}-{b:04X}" if a != b else f"{a:04X}" for a, b in rs[:40]), "..." if len(rs) > 40 else "", f"({len(o['map'])} chars)")
