"""Nintendo DS graphics: D2KP container (.pbg / .pobj) -> NCLR palette + NCGR tiles + NSCR screen map; PNG rendering.

D2KP = 0x58-byte header, then standard NitroSystem files back to back (each has its file size at +8):
  .pbg  : NCLR (RLCN) + NCGR (RGCN) + NSCR (RCSN)
  .pobj : NCLR + NCGR + NCER (RECN) + NANR (RNAN)
"""
import struct, sys
from PIL import Image

HDR = 0x58


def sections(d):
    """-> (list of (magic, offset, size) for the Nitro files in a D2KP blob, end offset).
    The container pads between files, so they are located by magic + byte-order mark rather than by walking sizes."""
    assert d[:4] == b"D2KP", "not D2KP"
    import re
    out = []
    for m in re.finditer(rb"(RLCN|RGCN|RCSN|RECN|RNAN)\xff\xfe[\x00\x01]\x01", d[HDR:]):
        pos = HDR + m.start()
        out.append((m.group(1).decode(), pos, struct.unpack_from("<I", d, pos + 8)[0]))
    end = out[-1][1] + out[-1][2] if out else HDR
    return out, end


def parse(d):
    secs, end = sections(d)
    info = {"sections": secs, "end": end, "len": len(d)}
    for magic, pos, size in secs:
        if magic == "RLCN":
            # file hdr 16, TTLP block: tag,size,depth(u32),pad(u32),datasize(u32),dataoff(u32)
            depth, _, dsize, doff = struct.unpack_from("<IIII", d, pos + 16 + 8)
            base = pos + 16 + 8 + doff        # data offset counts from the end of the 8-byte block header
            n = min(dsize, size - 16 - doff) // 2
            cols = []
            for i in range(n):
                v = struct.unpack_from("<H", d, base + 2 * i)[0]
                cols.append((((v & 31) * 255) // 31, (((v >> 5) & 31) * 255) // 31, (((v >> 10) & 31) * 255) // 31))
            info["pal"] = cols; info["pal_depth"] = depth; info["pal_off"] = base
        elif magic == "RGCN":
            # RAHC block: tag,size,th(u16),tw(u16),depth(u32),pad(u32),tiled(u32),datasize(u32),dataoff(u32)
            th, tw, depth, _, tiled, dsize, doff = struct.unpack_from("<HHIIIII", d, pos + 16 + 8)
            info.update(tiles_h=th, tiles_w=tw, bpp=4 if depth == 3 else 8, tiled=tiled, tile_off=pos + 16 + 8 + doff, tile_size=dsize)
        elif magic == "RCSN":
            # NRCS block: tag,size,w(u16),h(u16),pad(u32),datasize(u32)
            w, h, _, dsize = struct.unpack_from("<HHII", d, pos + 16 + 8)
            info.update(scr_w=w, scr_h=h, scr_off=pos + 16 + 20, scr_size=dsize)
    if "scr_off" in info and "tile_off" in info:
        per = 32 if info["bpp"] == 4 else 64
        ents = [struct.unpack_from("<H", d, info["scr_off"] + 2 * i)[0] for i in range(info["scr_size"] // 2)]
        nt = info["tile_size"] // per
        # long pages: one tile per cell; the 10-bit tile number in the map wraps after 1024 and is not what the engine uses
        info["identity"] = nt > 1024 and len(ents) == nt and all((e & 0x3FF) == (i & 0x3FF) and not (e >> 10) & 3 for i, e in enumerate(ents))
    return info


def tile_pixels(d, info):
    """Decode all tiles to lists of 64 palette indices."""
    off, size, bpp = info["tile_off"], info["tile_size"], info["bpp"]
    bytes_per = 32 if bpp == 4 else 64
    tiles = []
    for t in range(size // bytes_per):
        b = d[off + t * bytes_per: off + (t + 1) * bytes_per]
        if bpp == 4:
            px = []
            for byte in b:
                px += [byte & 15, byte >> 4]
        else:
            px = list(b)
        tiles.append(px)
    return tiles


def cell_ref(info, v, i):
    """(tile index, hflip, vflip, palette bank) for map entry v of cell i."""
    if info.get("identity"):
        return i, 0, 0, v >> 12
    return v & 0x3FF, (v >> 10) & 1, (v >> 11) & 1, v >> 12


def render_screen(d, info):
    """NSCR + NCGR + NCLR -> RGB image (width x height from NSCR)."""
    tiles = tile_pixels(d, info); pal = info["pal"]
    W, H = info["scr_w"], info["scr_h"]
    img = Image.new("RGB", (W, H)); px = img.load()
    n = info["scr_size"] // 2
    for i in range(n):
        v = struct.unpack_from("<H", d, info["scr_off"] + 2 * i)[0]
        idx, hf, vf, pn = cell_ref(info, v, i)
        tx, ty = i % (W // 8), i // (W // 8)
        if idx >= len(tiles) or ty * 8 >= H:
            continue
        t = tiles[idx]
        for y in range(8):
            for x in range(8):
                sx = 7 - x if hf else x; sy = 7 - y if vf else y
                c = t[sy * 8 + sx]
                if info["bpp"] == 4:
                    c += pn * 16
                px[tx * 8 + x, ty * 8 + y] = pal[c] if c < len(pal) else (255, 0, 255)
    return img


def render_tiles(d, info, cols=32):
    """Tile sheet (for .pobj or when there is no screen map)."""
    tiles = tile_pixels(d, info); pal = info["pal"]
    rows = (len(tiles) + cols - 1) // cols
    img = Image.new("RGB", (cols * 8, rows * 8)); px = img.load()
    for i, t in enumerate(tiles):
        tx, ty = i % cols, i // cols
        for y in range(8):
            for x in range(8):
                c = t[y * 8 + x]
                px[tx * 8 + x, ty * 8 + y] = pal[c] if c < len(pal) else (255, 0, 255)
    return img


def _entries(d, info):
    n = info["scr_size"] // 2
    return [struct.unpack_from("<H", d, info["scr_off"] + 2 * i)[0] for i in range(n)]


def _flip(px, hf, vf):
    return [px[(7 - y if vf else y) * 8 + (7 - x if hf else x)] for y in range(8) for x in range(8)]


def decode_indexed(d, info):
    """-> rows of absolute palette indices (4 bpp: bank*16 + colour). Cells that point past the tile data become 0."""
    tiles = tile_pixels(d, info); W, H = info["scr_w"], info["scr_h"]
    rows = [[0] * W for _ in range(H)]
    for i, v in enumerate(_entries(d, info)):
        idx, hf, vf, pn = cell_ref(info, v, i)
        tx, ty = i % (W // 8), i // (W // 8)
        if idx >= len(tiles) or ty * 8 >= H:
            continue
        t = _flip(tiles[idx], hf, vf)
        base = pn * 16 if info["bpp"] == 4 else 0
        for y in range(8):
            for x in range(8):
                rows[ty * 8 + y][tx * 8 + x] = t[y * 8 + x] + base
    return rows


def _pack_tile(px, bpp):
    if bpp == 8:
        return bytes(px)
    return bytes((px[2 * i] & 15) | ((px[2 * i + 1] & 15) << 4) for i in range(32))


def repack(d, info, rows):
    """New .pbg bytes in which the screen shows `rows` (absolute palette indices, same size as the original).
    Unchanged cells keep their map entries; changed cells reuse an identical tile (also flipped) or append a new one."""
    bpp, W, H = info["bpp"], info["scr_w"], info["scr_h"]
    tiles = tile_pixels(d, info); ents = _entries(d, info); cols = W // 8
    orig = decode_indexed(d, info)
    if info.get("identity"):
        return _repack_identity(d, info, rows, orig, tiles, ents)
    lookup = {}
    for i, t in enumerate(tiles):
        lookup.setdefault(tuple(t), i)
    new_tiles = []
    changed = 0
    for i in range(len(ents)):
        tx, ty = i % cols, i // cols
        if ty * 8 >= H:
            break
        cell = [rows[ty * 8 + y][tx * 8 + x] for y in range(8) for x in range(8)]
        old = [orig[ty * 8 + y][tx * 8 + x] for y in range(8) for x in range(8)]
        if cell == old:
            continue
        changed += 1
        if bpp == 4:
            banks = {v >> 4 for v in cell}
            if len(banks) != 1:
                raise ValueError(f"cell ({tx},{ty}) uses several palette banks {sorted(banks)}")
            bank = banks.pop(); px = [v & 15 for v in cell]
        else:
            bank, px = 0, list(cell)
        entry = None
        for hf in (0, 1):
            for vf in (0, 1):
                j = lookup.get(tuple(_flip(px, hf, vf)))      # flipping is an involution
                if j is not None:
                    entry = (j, hf, vf); break
            if entry:
                break
        if entry is None:
            j = len(tiles) + len(new_tiles)
            if j > 1023:
                raise ValueError("more than 1024 tiles needed")
            new_tiles.append(px); lookup[tuple(px)] = j; entry = (j, 0, 0)
        ents[i] = entry[0] | entry[1] << 10 | entry[2] << 11 | bank << 12
    out = bytearray(d)
    for i, v in enumerate(ents):
        struct.pack_into("<H", out, info["scr_off"] + 2 * i, v)
    if new_tiles:
        out = _append_tiles(out, info, new_tiles)
    return bytes(out), changed, len(new_tiles)


def _repack_identity(d, info, rows, orig, tiles, ents):
    """One tile per cell: overwrite the tile of every changed cell in place (no size change, no tile limit)."""
    bpp, W, H = info["bpp"], info["scr_w"], info["scr_h"]
    per = 32 if bpp == 4 else 64
    out = bytearray(d); cols = W // 8; changed = 0
    for i in range(len(ents)):
        tx, ty = i % cols, i // cols
        if ty * 8 >= H:
            break
        cell = [rows[ty * 8 + y][tx * 8 + x] for y in range(8) for x in range(8)]
        old = [orig[ty * 8 + y][tx * 8 + x] for y in range(8) for x in range(8)]
        if cell == old:
            continue
        changed += 1
        if bpp == 4:
            banks = {v >> 4 for v in cell}
            if len(banks) != 1:
                raise ValueError(f"cell ({tx},{ty}) uses several palette banks {sorted(banks)}")
            bank = banks.pop(); px = [v & 15 for v in cell]
            ents[i] = (ents[i] & 0x0FFF) | bank << 12
            struct.pack_into("<H", out, info["scr_off"] + 2 * i, ents[i])
        else:
            px = cell
        off = info["tile_off"] + i * per
        out[off: off + per] = _pack_tile(px, bpp)
    return bytes(out), changed, 0


def _append_tiles(out, info, new_tiles):
    """Grow the NCGR tile area: rewrite RGCN (RAHC header sizes/dims, tile data, SOPC dims) and the D2KP span in the header."""
    bpp = info["bpp"]
    data = bytearray(out[info["tile_off"]: info["tile_off"] + info["tile_size"]])
    for px in new_tiles:
        data += _pack_tile(px, bpp)
    return _set_tile_data(out, info, data)


def _set_tile_data(out, info, data):
    """Replace the whole NCGR tile area with `data` (any number of tiles)."""
    bpp = info["bpp"]; per = 32 if bpp == 4 else 64
    gpos, gsize = [(p, sz) for m, p, sz in info["sections"] if m == "RGCN"][0]
    tw = info["tiles_w"]
    data = bytearray(data)
    ntiles = len(data) // per
    th = (ntiles + tw - 1) // tw
    data += bytes(th * tw * per - len(data))
    head = bytearray(out[gpos: info["tile_off"]])               # NCGR file header (16) + RAHC header (32)
    tail = bytearray(out[info["tile_off"] + info["tile_size"]: gpos + gsize])     # SOPC block
    struct.pack_into("<I", head, 16 + 4, 0x20 + len(data))      # RAHC block size
    struct.pack_into("<HH", head, 16 + 8, th, tw)               # tiles high, tiles wide
    struct.pack_into("<I", head, 16 + 24, len(data))            # tile data size
    if tail[:4] == b"SOPC":
        struct.pack_into("<HH", tail, 12, tw, th)
    newg = bytearray(head + data + tail)
    struct.pack_into("<I", newg, 8, len(newg))                  # NCGR file size
    span_old = (gsize + 4) & ~3
    span_new = (len(newg) + 4) & ~3
    res = bytearray(out[:gpos]) + newg + bytes(span_new - len(newg)) + out[gpos + span_old:]
    struct.pack_into("<I", res, 7 * 4, span_new)               # D2KP header dword 7 = NCGR span
    return res


def compact(d):
    """Drop tiles that no map entry uses (keeps first-use order); flips and palette banks are untouched. Returns new bytes."""
    info = parse(d); bpp = info["bpp"]; per = 32 if bpp == 4 else 64
    ents = _entries(d, info); tdata = d[info["tile_off"]: info["tile_off"] + info["tile_size"]]
    order = []; remap = {}; seen = {}
    for e in ents:
        j = e & 0x3FF
        if j not in remap:
            key = bytes(tdata[j * per:(j + 1) * per])      # identical tiles share one slot
            if key not in seen: seen[key] = len(order); order.append(j)
            remap[j] = seen[key]
    out = bytearray(d)
    for i, e in enumerate(ents):
        struct.pack_into("<H", out, info["scr_off"] + 2 * i, (e & ~0x3FF) | remap[e & 0x3FF])
    data = b"".join(tdata[j * per:(j + 1) * per] for j in order)
    return bytes(_set_tile_data(out, info, data))


if __name__ == "__main__":
    d = open(sys.argv[1], "rb").read(); info = parse(d)
    print({k: (v if k not in ("pal",) else f"{len(v)} colours") for k, v in info.items()})
    img = render_screen(d, info) if "scr_w" in info else render_tiles(d, info)
    img.save(sys.argv[2]); print("saved", sys.argv[2], img.size)
