"""Отчёт: у каких блоков кегль меньше 27 и почему (не помещается в 3 ряда или не хватает секторов контейнера).
python3 -I scripts/ps2_fonts_report.py  — собирает блоки как ps2_all (без записи) и печатает по блокам: файл, блок, минимальный кегль по рядам, итоговый."""
import sys, os, csv, collections
sys.path.insert(0, os.path.dirname(__file__))
import ps2_scene as P, ps2_all as A, ps2_build as B
ru = A.load_ru()
mp = collections.defaultdict(dict)
for r in csv.DictReader(open('text/ps2/map.tsv', encoding='utf-8'), delimiter='\t'):
    if r['ID'] and r['яп_без_перевода'] != '1': mp[(r['файл'], int(r['блок']))][int(r['строка'])] = (r['сцена'], r['ID'])
for r in csv.DictReader(open('text/ps2/ru_ps2only.tsv', encoding='utf-8'), delimiter='\t'):
    if r['текст'].strip():
        key = ('PS2', '%s:%s:%s' % (r['файл'], r['блок'], r['строка'])); mp[(r['файл'], int(r['блок']))][int(r['строка'])] = key; ru[key] = r['текст'].strip()
fonts = {sz: B.load_font(A.FONT, sz, 'Bold') for sz in range(27, 17, -1)}
res = []
with open(A.ISO, 'rb') as iso:
    for fn in sorted({k[0] for k in mp}):
        lba, size = A.iso_find(iso, 'DATA/EVENT/' + fn); iso.seek(lba * 2048); d = iso.read(size); ents = P.parse_container(d)
        for b in sorted(b for (f, b) in mp if f == fn):
            s, z = ents[b]; blk = d[s * 2048:s * 2048 + z]; sc = P.parse_scene(blk)
            lines = [ru.get(mp[(fn, b)].get(i)) if mp[(fn, b)].get(i) else None for i in range(sc['nlines'])]
            if not any(lines): continue
            rows_sz = secs_sz = None; osec = (z + 2047) // 2048
            for sz in range(27, 17, -1):
                try: nb = B.build_scene(blk, lines, fonts[sz], A.MAXW)
                except ValueError as e:
                    continue
                if rows_sz is None: rows_sz = sz
                if (len(nb) + 2047) // 2048 <= osec: secs_sz = sz; break
            res.append((fn, b, rows_sz, secs_sz))
c = collections.Counter()
for fn, b, r, s in res:
    c[(r if r else 0, s if s else 0)] += 1
    if (r or 0) < 27 or (s or 0) < 27: print(fn, b, 'по рядам', r, 'по секторам', s)
print(sorted(c.items()))
