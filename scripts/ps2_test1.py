"""PS2, опыт 1: подмена первой реплики пролога (OP.BIN, блок 26) на месте, без смены размера.

Берёт английский образ, копирует в build/ps2/test1.iso, перерисовывает глифы 0..N атласа
кириллицей (Nunito), правит их записи и первый ряд первой строки. Остальные строки сцены
станут мусором, это нормально для опыта.

python3 -I scripts/ps2_test1.py   (запускать через tools/venv/bin/python)
"""
import os
import shutil
import struct
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(__file__))
import ps2_scene as P

ISO = 'roms/Hana to Taiyou to Ame to (English v1.0).iso'
OUT = 'build/ps2/test1.iso'
OP_LBA = 305485
BLOCK = 26
TEXT = 'Ладно, буду краток.'
FONT = 'tools/fonts/nunito/Nunito.ttf'
SIZE = 27
BASE = 24  # базовая линия в ячейке 32 px (у английской «O» дно на строке 24)


def render_glyph(font, ch):
    adv = font.getlength(ch)
    w = int(round(adv)) + 2
    im = Image.new('L', (w, 32), 0)
    ImageDraw.Draw(im).text((1, BASE), ch, font=font, fill=255, anchor='ls')
    return im, w


def main():
    f = open(ISO, 'rb')
    f.seek(OP_LBA * 2048)
    cont = f.read(14812 * 2048)
    ents = P.parse_container(cont)
    s, z = ents[BLOCK]
    b = bytearray(cont[s * 2048:s * 2048 + z])
    sc = P.parse_scene(bytes(b))
    px, off = P.atlas(bytes(b), sc['off_gs'])

    font = ImageFont.truetype(FONT, SIZE)
    font.set_variation_by_name('SemiBold')
    chars = []
    for ch in TEXT:
        if ch != ' ' and ch not in chars:
            chars.append(ch)
    row0 = sc['lines'][0]['rows'][0]
    assert len(row0) == 25 and len(chars) <= 18
    # новые глифы: ячейки в свободной нижней части атласа (y >= 288)
    new = {}
    for k, ch in enumerate(chars):
        im, w = render_glyph(font, ch)
        x, y = (k % 9) * 28, 288 + (k // 9) * 32
        for yy in range(32):
            for xx in range(w):
                px[y + yy][x + xx] = 1 if im.getpixel((xx, yy)) >= 128 else 0
        new[ch] = (k, w, x, y)
        # запись глифа k (индексы 0..): u32 0, w, h, u, v
        struct.pack_into('<IHHff', b, 0x74 + 16 * k, 0, w, 32, x / 256, y / 512)
    idx = []
    for ch in TEXT:
        idx.append(P.SPACE if ch == ' ' else new[ch][0])
    idx += [P.SPACE] * (25 - len(idx))
    # первый ряд первой строки: смещение ряда из таблицы
    ln = struct.unpack_from('<I', b, 0x18)[0]
    line_off = ln
    rt = struct.unpack_from('<I', b, line_off + 0x18)[0]
    struct.pack_into('<25H', b, line_off + rt + 4, *idx)
    # атлас обратно (линейно, 2 пикселя на байт)
    data = bytearray()
    for r in px:
        for i in range(0, 256, 2):
            data.append(r[i] | (r[i + 1] << 4))
    b[off:off + 0x10000] = data

    os.makedirs('build/ps2', exist_ok=True)
    shutil.copyfile(ISO, OUT)
    with open(OUT, 'r+b') as o:
        o.seek((OP_LBA + s) * 2048)
        o.write(bytes(b))
    print('готово', OUT, 'блок', BLOCK, 'сектор', s, 'размер', z)


if __name__ == '__main__':
    main()
