"""PS2: разбор контейнеров DATA/EVENT/*.BIN (LF?) и блоков сцен с репликами.

Контейнер: 'LF' + байт + 0, дальше слова u32; w[3] = размер таблицы в секторах (2048),
w[2] = размер самой таблицы-заголовка в байтах (блок 0), затем пары (сектор, размер).

Блок сцены (первое u16 = число строк):
  u16 nlines, u16 ntex, u16 nglyph, u16 0x200
  u32 off_lines(=0x18), u32 off_end_lines, u32 off_glyphs, u32 off_glyphs_end
  u32[nlines] смещения строк
  u32 размер текстуры в GS, u32 0
  глифы по 16 байт: u32 0, u16 w, u16 h(32), f32 u, f32 v  (x=u*256, y=v*512)
  строки: 8 байт флагов (байт 2 = число рядов, 4..7 = стиль), 0x18, 12 нулевых байт,
          таблица смещений рядов (u32 на ряд, от начала строки), ряды: u32 n, n*u16 индексов
          глифов (0x8400 = пробел), выравнивание до 4
  с off_end_lines: GS-пакеты (BITBLTBUF/TRXREG/IMAGE); первая загрузка 256x512 4 bpp, линейная
          раскладка, 64 КБ, начало данных = смещение первой IMAGE-метки + 16
"""
import struct
import sys

SPACE = 0x8400


def parse_container(d):
    assert d[:2] == b'LF'
    hdr_words = struct.unpack_from('<I', d, 12)[0] * 512
    w = struct.unpack_from('<%dI' % hdr_words, d, 0)
    ents = [(0, w[2])]
    i = 3
    while True:
        s, z = w[i], w[i + 1]
        if s == 0 or s * 2048 > len(d) or s * 2048 + z > len(d) + 2048:
            break
        ents.append((s, z))
        i += 2
    return ents


def parse_scene(b):
    nlines, ntex, nglyph, _ = struct.unpack_from('<4H', b, 0)
    off_lines, off_lines_end, off_gl, off_gl_end = struct.unpack_from('<4I', b, 8)
    assert off_gl_end - off_gl == 16 * nglyph, 'не сцена'
    offs = list(struct.unpack_from('<%dI' % nlines, b, off_lines))
    glyphs = []
    for k in range(nglyph):
        _, w, h, u, v = struct.unpack_from('<IHHff', b, off_gl + 16 * k)
        glyphs.append(dict(w=w, h=h, x=round(u * 256), y=round(v * 512)))
    lines = []
    ends = offs[1:] + [off_lines_end_pad(b, off_lines_end, offs, nlines)]
    for s, e in zip(offs, ends):
        flags = b[s:s + 8]
        nrows = flags[2]
        rt = struct.unpack_from('<%dI' % nrows, b, s + 0x18)
        rows = []
        for r in rt:
            n = struct.unpack_from('<I', b, s + r)[0]
            rows.append(list(struct.unpack_from('<%dH' % n, b, s + r + 4)))
        lines.append(dict(flags=flags, rows=rows))
    return dict(nlines=nlines, ntex=ntex, glyphs=glyphs, lines=lines, off_gs=off_lines_end_pad(b, off_lines_end, offs, nlines))


def off_lines_end_pad(b, off_lines_end, offs, nlines):
    # конец последней строки = начало GS-пакетов (смещение записано в u32 по off_lines_end - ... нет,
    # берём из таблицы заголовка: последняя запись + длина). Пакеты начинаются с DMA-тега 0x10 0x10 0x00 0x20.
    i = b.find(b'\x10\x10\x00\x20', offs[-1])
    return i


def atlas(b, gs_off):
    """Первая GS-загрузка 256x512 4 bpp, линейно: возвращает список строк по 256 индексов 0..15."""
    i = b.find(b'\x00\x10\x00\x00\x00\x00\x00\x08', gs_off)  # IMAGE-метка nloop=0x1000
    data = b[i + 8 + 8:i + 16 + 0x10000]
    rows = []
    for y in range(512):
        row = []
        for v in data[y * 128:(y + 1) * 128]:
            row += [v & 15, v >> 4]
        rows.append(row)
    return rows, i + 16


def render_png(path, rows, scale=1):
    from PIL import Image
    img = Image.new('L', (256, len(rows)))
    img.putdata([p * 17 for r in rows for p in r])
    if scale != 1:
        img = img.resize((256 * scale, len(rows) * scale))
    img.save(path)


def render_line(sc, rows_px, row, space=10):
    from PIL import Image
    g = sc['glyphs']
    w = sum(space if i == SPACE else g[i]['w'] for i in row)
    img = Image.new('L', (max(w, 1), 32), 255)
    x = 0
    for i in row:
        if i == SPACE:
            x += space
            continue
        gl = g[i]
        for yy in range(32):
            for xx in range(gl['w']):
                p = rows_px[gl['y'] + yy][gl['x'] + xx]
                img.putpixel((x + xx, yy), 255 if p == 0 else int(40 + (p - 1) * 15))
        x += gl['w']
    return img


if __name__ == '__main__':
    path, k = sys.argv[1], int(sys.argv[2])
    d = open(path, 'rb').read()
    ents = parse_container(d)
    s, z = ents[k]
    b = d[s * 2048:s * 2048 + z]
    sc = parse_scene(b)
    print(len(ents), 'entries; scene', k, 'lines', sc['nlines'], 'glyphs', len(sc['glyphs']), 'gs at', hex(sc['off_gs']))
    px, off = atlas(b, sc['off_gs'])
    print('atlas data at', hex(off))
    if len(sys.argv) > 3:
        from PIL import Image
        out = sys.argv[3]
        render_png(out + '_atlas.png', px)
        lines = [render_line(sc, px, r) for ln in sc['lines'] for r in ln['rows']]
        W = max(i.width for i in lines)
        sheet = Image.new('L', (W, 34 * len(lines)), 255)
        for n, im in enumerate(lines):
            sheet.paste(im, (0, 34 * n))
        sheet.save(out + '_lines.png')
