"""PS2, опыт 2: вся сцена пролога (OP.BIN, блок 26) по-русски из text/ru/C00_01.txt.
Запуск: tools/venv/bin/python -I scripts/ps2_test2.py [вес шрифта]"""
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(__file__))
import ps2_build as B
import ps2_scene as P

ISO = 'roms/Hana to Taiyou to Ame to (English v1.0).iso'
OUT = os.environ.get('OUT', 'build/ps2/test3.iso')
OP_LBA, OP_SECT = 305485, 14812
FONT = 'tools/fonts/nunito/Nunito.ttf'
# звезда F.S.R. справа начинается примерно с 390 px от начала текста (проверено в игре 2026-10-23)
MAXW_SCREEN = 365


def read_tr(path, first, count):
    ids = {}
    cur = None
    for ln in open(path, encoding='utf-8').read().split('\n'):
        if ln.strip().isdigit() and len(ln.strip()) == 5:
            cur = ln.strip()
            ids[cur] = []
        elif cur is not None and ln != '':
            ids[cur].append(ln)
    return [' '.join(ids['%05d' % (first + i)]) for i in range(count)]


def main():
    var = sys.argv[1] if len(sys.argv) > 1 else 'Bold'
    with open(ISO, 'rb') as f:
        f.seek(OP_LBA * 2048)
        cont = f.read(OP_SECT * 2048)
    ents = P.parse_container(cont)
    s, z = ents[26]
    blk = cont[s * 2048:s * 2048 + z]
    sc = P.parse_scene(blk)
    # предел ширины ряда: самый широкий английский ряд сцены
    g = sc['glyphs']
    maxw = max(sum(B.SPACE_W if i == P.SPACE else g[i]['w'] for i in r) for ln in sc['lines'] for r in ln['rows'])
    maxw = min(maxw, MAXW_SCREEN)
    print('предел ширины ряда', maxw)
    ru = read_tr('text/ru/C00_01.txt', 1001 + 0, sc['nlines'])
    font = B.load_font(FONT, 27, var)
    new = B.build_scene(blk, ru, font, maxw)
    print('блок', len(blk), '->', len(new))
    cont2 = B.repack_container(cont, {26: new})
    os.makedirs('build/ps2', exist_ok=True)
    shutil.copyfile(ISO, OUT)
    with open(OUT, 'r+b') as o:
        o.seek(OP_LBA * 2048)
        o.write(cont2)
    print('готово', OUT)


if __name__ == '__main__':
    main()
