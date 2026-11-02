"""PS2: сборка блока сцены с русским текстом и перепаковка контейнера LF.

build_scene(block, ru_lines, font) -> bytes   новый блок (глифы, строки, атлас пересобираются)
repack_container(data, new_blocks) -> bytes   тот же размер, сектора пересчитаны, или ValueError
"""
import struct

from PIL import Image, ImageDraw, ImageFont

import ps2_scene as P

SPACE_W = 10
BASE = 24
ROW_MAX = 3


def load_font(path, size=27, var='Bold'):
    f = ImageFont.truetype(path, size)
    f.set_variation_by_name(var)
    return f


def coverage_to_index(c):
    """Палитра текста: 0 прозрачно, 1..15 по убыванию непрозрачности (проверено пробой в игре)."""
    if c < 0.03:
        return 0
    return max(1, min(15, 16 - int(round(c * 15))))


def glyph_bitmap(font, ch):
    w = int(round(font.getlength(ch))) + 2
    im = Image.new('L', (w, 32), 0)
    ImageDraw.Draw(im).text((1, BASE), ch, font=font, fill=255, anchor='ls')
    return [[coverage_to_index(im.getpixel((x, y)) / 255) for x in range(w)] for y in range(32)], w


def text_width(text, widths):
    return sum(SPACE_W if c == ' ' else widths[c] for c in text)


def wrap(text, widths, maxw):
    words = text.split()
    rows, cur = [], ''
    for w in words:
        t = (cur + ' ' + w) if cur else w
        if text_width(t, widths) <= maxw or not cur:
            cur = t
        else:
            rows.append(cur)
            cur = w
    rows.append(cur)
    return rows


def pad(b, n):
    return b + b'\0' * (-len(b) % n)


def build_scene(block, ru_lines, font, maxw, atlas_rows=512, first_y=288, dedupe=False):
    """ru_lines[i] = русский текст или None (строка остаётся как есть: её глифы сохраняются на местах)."""
    sc = P.parse_scene(block)
    assert len(ru_lines) == sc['nlines'], (len(ru_lines), sc['nlines'])
    gs = sc['off_gs']
    px, atlas_off = P.atlas(block, gs)
    old_g = sc['glyphs']
    # глифы нетронутых строк: остаются на своих местах
    kept = []
    for i, t in enumerate(ru_lines):
        if t is None:
            for r in sc['lines'][i]['rows']:
                for g in r:
                    if g != P.SPACE and g not in kept:
                        kept.append(g)
    chars = []
    for t in ru_lines:
        for c in (t or '').replace('\n', ' '):
            if c != ' ' and c not in chars:
                chars.append(c)
    bm, widths = {}, {}
    for c in chars:
        bm[c], widths[c] = glyph_bitmap(font, c)
    # упаковка новых глифов в свободную часть атласа (ниже first_y, мимо сохранённых)
    busy = [(old_g[g]['x'], old_g[g]['y'], old_g[g]['w']) for g in kept]

    def free(x, y, w):
        return all(not (x < bx + bw and bx < x + w and y < by + 32 and by < y + 32) for bx, by, bw in busy)
    pos = {}
    for c in sorted(chars, key=lambda c: -widths[c]):
        w = widths[c]
        done = False
        y = first_y
        while y + 32 <= atlas_rows and not done:
            x = 0
            while x + w <= 256:
                if free(x, y, w):
                    pos[c] = (x, y)
                    busy.append((x, y, w))
                    done = True
                    break
                x += 1
            y += 32
        if not done:
            raise ValueError('атлас переполнен')
        x, y = pos[c]
        for yy in range(32):
            for xx in range(w):
                px[y + yy][x + xx] = bm[c][yy][xx]
    # новая таблица глифов: сначала сохранённые, потом новые
    gl = [(old_g[g]['w'], old_g[g]['x'], old_g[g]['y']) for g in kept] + [(widths[c],) + pos[c] for c in chars]
    gidx = {c: len(kept) + i for i, c in enumerate(chars)}
    kidx = {g: i for i, g in enumerate(kept)}
    # строки
    recs = []
    for i, t in enumerate(ru_lines):
        old = sc['lines'][i]
        if t is None:
            rows_idx = [[P.SPACE if g == P.SPACE else kidx[g] for g in r] for r in old['rows']]
            flags = bytes(old['flags'])
        else:
            rows = wrap(t.replace('\n', ' '), widths, maxw)
            if len(rows) > ROW_MAX:
                raise ValueError('строка %d: %d рядов' % (i, len(rows)))
            rows_idx = [[P.SPACE if c == ' ' else gidx[c] for c in r] for r in rows]
            flags = bytes([old['flags'][0], old['flags'][1], len(rows), old['flags'][3]]) + bytes(old['flags'][4:8])
        ptrs, body, off = [], b'', 0x18 + 4 * len(rows_idx)
        for idx in rows_idx:
            ptrs.append(off)
            chunk = pad(struct.pack('<I', len(idx)) + struct.pack('<%dH' % len(idx), *idx), 4)
            body += chunk
            off += len(chunk)
        rec = flags + struct.pack('<I', 0x18) + b'\0' * 12 + struct.pack('<%dI' % len(ptrs), *ptrs) + body
        recs.append(rec)
    nl, ng = len(recs), len(gl)
    off_lines = 0x18
    off_lines_end = off_lines + 4 * nl
    off_gl = off_lines_end + 8
    off_gl_end = off_gl + 16 * ng
    pos0 = off_gl_end + 12
    offs, cur, seen, uniq = [], pos0, {}, []
    for r in recs:
        if dedupe and r in seen:      # одинаковые реплики делят одну запись (экономия места)
            offs.append(seen[r])
            continue
        seen[r] = cur
        offs.append(cur)
        uniq.append(r)
        cur += len(r)
    recs = uniq
    new_gs = (cur + 15) // 16 * 16
    ntex = sc['ntex']
    old_hdr = struct.unpack_from('<2I', block, off_lines_end_of(block))
    second = old_hdr[1]
    if ntex == 2:
        second += new_gs - gs
    out = bytearray()
    out += struct.pack('<4H', nl, ntex, ng, 0x200)
    out += struct.pack('<4I', off_lines, off_lines_end, off_gl, off_gl_end)
    out += struct.pack('<%dI' % nl, *offs)
    out += struct.pack('<2I', new_gs, second)
    bval = struct.unpack_from('<I', block, struct.unpack_from('<I', block, 16)[0])[0]
    for w, x, y in gl:
        out += struct.pack('<IHHff', bval, w, 32, x / 256, y / 512)
    out += b'\0' * 12
    for r in recs:
        out += r
    out = pad(bytes(out), 16)
    assert len(out) == new_gs
    tail = bytearray(block[gs:])
    # атлас первой текстуры (линейно, 2 пикселя в байте)
    data = bytearray()
    for r in px:
        for i in range(0, 256, 2):
            data.append(r[i] | (r[i + 1] << 4))
    ao = atlas_off - gs
    tail[ao:ao + 0x10000] = data
    return bytes(out) + bytes(tail)


def off_lines_end_of(block):
    return struct.unpack_from('<I', block, 12)[0]


def repack_container(data, new_blocks):
    """new_blocks: {номер: bytes}. Блоки до первого изменённого остаются на местах, дальше
    идут впритык (начало на границе сектора). Размер файла не меняется, иначе ValueError."""
    ents = P.parse_container(data)
    first = min(new_blocks)
    buf = bytearray(data)
    sec = ents[first][0]
    for k in range(first, len(ents)):
        s, z = ents[k]
        blk = new_blocks.get(k, data[s * 2048:s * 2048 + z])
        if (sec + (len(blk) + 2047) // 2048) * 2048 > len(data):
            need = sum((len(new_blocks.get(j, b'x' * ents[j][1])) + 2047) // 2048 for j in range(first, len(ents)))
            have = len(data) // 2048 - ents[first][0]
            raise ValueError('контейнер вырос на %d секторов (блок %d не помещается)' % (need - have, k))
        buf[sec * 2048:(sec + (len(blk) + 2047) // 2048) * 2048] = b'\0' * ((len(blk) + 2047) // 2048 * 2048)
        buf[sec * 2048:sec * 2048 + len(blk)] = blk
        struct.pack_into('<2I', buf, 12 + 8 * (k - 1), sec, len(blk))
        sec += (len(blk) + 2047) // 2048
    # хвост после последнего блока чистим нулями, если контейнер стал короче
    buf[sec * 2048:] = b'\0' * (len(buf) - sec * 2048)
    return bytes(buf)
