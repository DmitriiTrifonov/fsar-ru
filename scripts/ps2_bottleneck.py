"""Какие реплики тянут кегль блока вниз: для каждой реплики минимальный кегль, при котором она влезает в 3 ряда по 365 px.
python3 -I scripts/ps2_bottleneck.py [порог=24]  — печатает реплики с кеглем ниже порога (файл блок строка сцена/ID кегль текст)."""
import sys, os, csv, collections
sys.path.insert(0, os.path.dirname(__file__))
import ps2_all as A, ps2_build as B
thr = int(sys.argv[1]) if len(sys.argv) > 1 else 24
ru = A.load_ru()
fonts = {sz: B.load_font(A.FONT, sz, 'Bold') for sz in range(27, 17, -1)}
wcache = {}
def widths(sz, text):
    f = fonts[sz]; c = wcache.setdefault(sz, {})
    for ch in set(text):
        if ch != ' ' and ch not in c: c[ch] = int(round(f.getlength(ch))) + int(os.environ.get('PAD', '1'))
    return c
rows = []
for r in csv.DictReader(open('text/ps2/map.tsv', encoding='utf-8'), delimiter='\t'):
    if r['ID'] and r['яп_без_перевода'] != '1':
        t = ru.get((r['сцена'], r['ID']))
        if t: rows.append((r['файл'], int(r['блок']), int(r['строка']), r['сцена'] + '/' + r['ID'], t))
for r in csv.DictReader(open('text/ps2/ru_ps2only.tsv', encoding='utf-8'), delimiter='\t'):
    if r['текст'].strip(): rows.append((r['файл'], int(r['блок']), int(r['строка']), 'PS2', r['текст'].strip()))
out = []
for fn, b, i, sid, t in rows:
    t1 = t.replace('\n', ' ')
    need = None
    for sz in range(27, 17, -1):
        w = widths(sz, t1)
        if len(B.wrap(t1, w, A.MAXW)) <= 3: need = sz; break
    if need is not None and need < thr: out.append((fn, b, i, sid, need, t1))
blocks = collections.Counter((o[0], o[1]) for o in out)
for o in sorted(out): print(*o[:5], o[5])
print(len(out), 'реплик в', len(blocks), 'блоках')
