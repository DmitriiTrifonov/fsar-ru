"""Статическая проверка PS2-образа без эмулятора: python3 -I scripts/ps2_audit.py [образ=build/ps2/rel.iso]
По каждой сцене с переводом: число рядов (<=3), ширина ряда (сумма ширин глифов, пробел 10) против MAXW=365 и против японского оригинала,
индексы глифов в пределах таблицы, глифы внутри атласа 256x512. Печатает самые широкие ряды и нарушения."""
import sys, os, csv, collections
sys.path.insert(0, os.path.dirname(__file__))
import ps2_scene as P, ps2_all as A
iso_path = sys.argv[1] if len(sys.argv) > 1 else 'build/ps2/rel.iso'
mp = collections.defaultdict(dict)
for r in csv.DictReader(open('text/ps2/map.tsv', encoding='utf-8'), delimiter='\t'):
    if r['ID'] and r['яп_без_перевода'] != '1': mp[(r['файл'], int(r['блок']))][int(r['строка'])] = (r['сцена'], r['ID'])
def rowset(iso, fn):
    lba, size = A.iso_find(iso, 'DATA/EVENT/' + fn); iso.seek(lba * 2048); d = iso.read(size); ents = P.parse_container(d); out = {}
    for (f, b), lines in mp.items():
        if f != fn: continue
        s, z = ents[b]; sc = P.parse_scene(d[s * 2048:s * 2048 + z]); out[b] = sc
    return out
def width(row, gl): return sum(A.B.SPACE_W if g == P.SPACE else (gl[g]['w'] if g < len(gl) else 0) for g in row)
bad, wide, stat = [], [], collections.Counter()
with open(iso_path, 'rb') as ru_iso, open(A.ISO, 'rb') as jp_iso:
    jpmax = 0
    for fn in sorted({k[0] for k in mp}):
        ru, jp = rowset(ru_iso, fn), rowset(jp_iso, fn)
        for b, sc in ru.items():
            gl = sc['glyphs']
            for i, (key) in mp[(fn, b)].items():
                ln = sc['lines'][i]; rows = ln['rows']; stat['реплик'] += 1
                if len(rows) > 3: bad.append((fn, b, i, key, 'рядов %d' % len(rows)))
                for r in rows:
                    if any(g != P.SPACE and g >= len(gl) for g in r): bad.append((fn, b, i, key, 'глиф вне таблицы')); continue
                    w = width(r, gl); wide.append((w, fn, b, i, key))
                    if w > A.MAXW: bad.append((fn, b, i, key, 'ряд %d px' % w))
            for g in gl:
                if g['x'] + g['w'] > 256 or g['y'] + g['h'] > 512: bad.append((fn, b, '-', '-', 'глиф вне атласа %s' % g))
            if b in jp:
                for i in mp[(fn, b)]:
                    for r in jp[b]['lines'][i]['rows']: jpmax = max(jpmax, width(r, jp[b]['glyphs']))
wide.sort(reverse=True)
print('реплик', stat['реплик'], '| ширина japan max', jpmax, '| ru max', wide[0][0], '| нарушений', len(bad))
for w in wide[:12]: print('широкий', *w)
for b in bad[:30]: print('НАРУШЕНИЕ', *b)
