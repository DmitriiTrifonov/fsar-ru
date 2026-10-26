"""PS2, проба палитры: первая реплика пролога (OP.BIN, блок 26) = 16 квадратов с индексами 0..15.
Правка на месте, без смены размера. Образ: build/ps2/probe.iso. Запуск: tools/venv/bin/python -I scripts/ps2_probe_palette.py"""
import os
import shutil
import struct
import sys

sys.path.insert(0, os.path.dirname(__file__))
import ps2_scene as P

ISO = 'roms/Hana to Taiyou to Ame to (English v1.0).iso'
OUT = 'build/ps2/probe.iso'
OP_LBA, OP_SECT, BLOCK = 305485, 14812, 26
W = 22


def main():
    with open(ISO, 'rb') as f:
        f.seek(OP_LBA * 2048)
        cont = f.read(OP_SECT * 2048)
    s, z = P.parse_container(cont)[BLOCK]
    b = bytearray(cont[s * 2048:s * 2048 + z])
    sc = P.parse_scene(bytes(b))
    px, off = P.atlas(bytes(b), sc['off_gs'])
    for i in range(16):
        x, y = (i % 8) * 28, 288 + (i // 8) * 32
        for yy in range(32):
            for xx in range(W):
                px[y + yy][x + xx] = i
        struct.pack_into('<IHHff', b, 0x74 + 16 * i, 0, W, 32, x / 256, y / 512)
    l0 = struct.unpack_from('<I', b, 0x18)[0]
    rt = struct.unpack_from('<I', b, l0 + 0x18)[0]
    struct.pack_into('<25H', b, l0 + rt + 4, *(list(range(16)) + [P.SPACE] * 9))
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
    print('готово', OUT)


if __name__ == '__main__':
    main()
