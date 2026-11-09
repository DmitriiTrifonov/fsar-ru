"""PS2: русификация всех сцен (DATA/EVENT/*.BIN) по text/ps2/map.tsv и text/ru.csv.

  tools/venv/bin/python -I scripts/ps2_all.py [--write build/ps2/all.iso] [--iso <японский образ>] [--only OP.BIN,R01.BIN]

Без --write — только проверка (ряды, атлас, размеры). Строки без соответствия в DS, без перевода
и «не переведённые в английском патче» остаются японскими.
"""
import argparse
import collections
import csv
import os
import shutil
import struct
import sys

sys.path.insert(0, os.path.dirname(__file__))
import ps2_build as B
import ps2_scene as P

ISO = 'roms/Hana to Taiyou to Ame to (Japan).iso'
FONT = 'tools/fonts/nunito/Nunito.ttf'
MAXW = 365


def iso_find(f, path):
    """(lba, size) файла в ISO9660 по пути вида DATA/EVENT/OP.BIN."""
    f.seek(16 * 2048)
    pvd = f.read(2048)
    root = struct.unpack_from('<I', pvd, 156 + 2)[0]
    rsize = struct.unpack_from('<I', pvd, 156 + 10)[0]
    lba, size = root, rsize
    for part in path.split('/'):
        f.seek(lba * 2048)
        d = f.read(size)
        p = 0
        while p < len(d):
            n = d[p]
            if n == 0:
                p = (p // 2048 + 1) * 2048
                continue
            name = d[p + 33:p + 33 + d[p + 32]].decode('ascii', 'replace').split(';')[0]
            if name.upper() == part.upper():
                lba, size = struct.unpack_from('<I', d, p + 2)[0], struct.unpack_from('<I', d, p + 10)[0]
                break
            p += n
        else:
            raise FileNotFoundError(path)
    return lba, size


def load_ru():
    ru = {}
    for r in csv.DictReader(open('text/ru.csv', encoding='utf-8')):
        t = r['Русский'].replace('\r', '').replace('\n', ' ').strip()
        if t:
            ru[(r['Сцена'], r['ID'])] = t
    # правки только для PS2 (текст DS не трогаем): text/ps2/ru_override.tsv, например чтобы блок влез в контейнер
    ov = 'text/ps2/ru_override.tsv'
    if os.path.exists(ov):
        for r in csv.DictReader(open(ov, encoding='utf-8'), delimiter='\t'):
            ru[(r['Сцена'], r['ID'])] = r['Текст'].strip()
    return ru


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--iso', default=ISO)
    ap.add_argument('--write')
    ap.add_argument('--only')
    a = ap.parse_args()
    ru = load_ru()
    mp = collections.defaultdict(dict)
    for r in csv.DictReader(open('text/ps2/map.tsv', encoding='utf-8'), delimiter='\t'):
        if r['ID'] and r['яп_без_перевода'] != '1':
            mp[(r['файл'], int(r['блок']))][int(r['строка'])] = (r['сцена'], r['ID'])
    # строки только PS2 (нет аналога в DS): text/ps2/ru_ps2only.tsv, ключ файл/блок/строка
    po = 'text/ps2/ru_ps2only.tsv'
    if os.path.exists(po):
        for r in csv.DictReader(open(po, encoding='utf-8'), delimiter='\t'):
            if r['текст'].strip():
                key = ('PS2', '%s:%s:%s' % (r['файл'], r['блок'], r['строка']))
                mp[(r['файл'], int(r['блок']))][int(r['строка'])] = key
                ru[key] = r['текст'].strip()
    fonts = [(sz, B.load_font(FONT, sz, 'Bold')) for sz in range(27, 17, -1)]
    files = sorted({k[0] for k in mp})
    if a.only:
        files = [f for f in files if f in a.only.split(',')]
    stat = collections.Counter()
    problems = []
    outputs = {}
    with open(a.iso, 'rb') as iso:
        for fn in files:
            lba, size = iso_find(iso, 'DATA/EVENT/' + fn)
            iso.seek(lba * 2048)
            data = iso.read(size)
            ents = P.parse_container(data)
            new, lines_of, size_of = {}, {}, {}
            for k in sorted(b for (f, b) in mp if f == fn):
                s, z = ents[k]
                blk = data[s * 2048:s * 2048 + z]
                sc = P.parse_scene(blk)
                lines = []
                for i in range(sc['nlines']):
                    key = mp[(fn, k)].get(i)
                    t = ru.get(key) if key else None
                    lines.append(t)
                    stat['ru' if t else 'jp'] += 1
                if not any(lines):
                    continue
                lines_of[k] = (blk, lines)
                size_of[k] = 0

            dedupe = set()

            def build(k):
                blk, lines = lines_of[k]
                while size_of[k] < len(fonts):
                    try:
                        new[k] = B.build_scene(blk, lines, fonts[size_of[k]][1], MAXW, dedupe=k in dedupe)
                        return True
                    except ValueError:
                        size_of[k] += 1
                new.pop(k, None)
                return False
            for k in lines_of:
                if not build(k):
                    problems.append((fn, k, 'не собрался даже мелким кеглем'))
            while True:
                try:
                    if new:
                        outputs[fn] = (lba, B.repack_container(data, new))
                    break
                except ValueError as e:
                    # уменьшаем кегль у блоков, выросших по секторам, и пробуем снова
                    grown = [k for k in new if (len(new[k]) + 2047) // 2048 > (ents[k][1] + 2047) // 2048
                             and size_of[k] + 1 < len(fonts)]
                    if not grown:
                        over = [k for k in new if (len(new[k]) + 2047) // 2048 > (ents[k][1] + 2047) // 2048
                                and k not in dedupe]
                        if not over:
                            # не влезает даже так: самый выросший блок остаётся японским
                            if not new:
                                problems.append((fn, '-', str(e)))
                                break
                            gr = [k for k in new if (len(new[k]) + 2047) // 2048 > (ents[k][1] + 2047) // 2048] or list(new)
                            gk = min(gr, key=lambda k: len(new[k]))
                            problems.append((fn, gk, 'не влез в контейнер, остаётся японским'))
                            del new[gk]
                            continue
                        k = max(over, key=lambda k: len(new[k]))
                        dedupe.add(k)
                        stat['общие записи реплик'] += 1
                        build(k)
                        continue
                    k = max(grown, key=lambda k: len(new[k]))
                    size_of[k] += 1
                    stat['ужато ради места'] += 1
                    if not build(k):
                        problems.append((fn, k, 'не собрался'))
                        break
            for k in new:
                stat['blocks'] += 1
                stat['кегль %d' % fonts[size_of[k]][0]] += 1
    print(dict(stat))
    for p in problems:
        print('ПРОБЛЕМА', *p)
    if a.write:
        os.makedirs(os.path.dirname(a.write), exist_ok=True)
        shutil.copyfile(a.iso, a.write)
        with open(a.write, 'r+b') as o:
            for fn, (lba, d) in outputs.items():
                o.seek(lba * 2048)
                o.write(d)
        print('записано', a.write, sorted(outputs))


if __name__ == '__main__':
    main()
