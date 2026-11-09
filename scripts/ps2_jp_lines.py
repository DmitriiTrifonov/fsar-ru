"""Нарисовать японские строки PS2, у которых нет перевода (нет английского аналога), для чтения глазами.
python3 -I scripts/ps2_jp_lines.py [файл.BIN]  →  dumps/ps2/jp/<файл>_<блок>.png (строки с подписью файл/блок/строка).
Берёт строки из text/ps2/map.tsv с флагом яп_без_перевода=1 или без ID."""
import sys, os, csv, collections
sys.path.insert(0, os.path.dirname(__file__))
import ps2_scene as P, ps2_all as A
from PIL import Image, ImageDraw
only = sys.argv[1] if len(sys.argv) > 1 else None
want = collections.defaultdict(list)
for r in csv.DictReader(open('text/ps2/map.tsv', encoding='utf-8'), delimiter='\t'):
    if (r['яп_без_перевода'] == '1' or not r['ID']) and (not only or r['файл'] == only):
        want[(r['файл'], int(r['блок']))].append((int(r['строка']), r['сцена'], r['ID']))
os.makedirs('dumps/ps2/jp', exist_ok=True)
cache = {}
pages = {}
with open(A.ISO, 'rb') as iso:
    for (fn, b), items in sorted(want.items()):
        if fn not in cache:
            lba, size = A.iso_find(iso, 'DATA/EVENT/' + fn); iso.seek(lba * 2048); d = iso.read(size); cache[fn] = (d, P.parse_container(d))
        d, ents = cache[fn]; s, z = ents[b]; blk = d[s * 2048:s * 2048 + z]; sc = P.parse_scene(blk); px, _ = P.atlas(blk, sc['off_gs'])
        ims = []
        for (i, scene, id_) in items:
            rows = [P.render_line(sc, px, [g for g in r if g == P.SPACE or g < len(sc['glyphs'])]) for r in sc['lines'][i]['rows']]
            h = 34 * len(rows) + 2; w = max(r.width for r in rows) + 150
            im = Image.new('L', (w, h), 255); d2 = ImageDraw.Draw(im); d2.text((2, 8), '%d %s %s' % (i, scene, id_), fill=0)
            for n, r in enumerate(rows): im.paste(r, (150, 34 * n))
            ims.append(im)
        pages.setdefault(fn, []).extend((b, im) for im in ims)
for fn, items in pages.items():   # листы по ~1300 px высотой, подпись у каждой строки: строка файл блок номер
    cur, h, n = [], 0, 0
    def flush():
        global cur, h, n
        if not cur: return
        W = max(i.width for _, i in cur); sheet = Image.new('L', (W + 60, h), 255); y = 0
        for b, i in cur:
            ImageDraw.Draw(sheet).text((2, y + 8), 'b%d' % b, fill=0); sheet.paste(i, (60, y)); y += i.height
        sheet.save('dumps/ps2/jp/%s_p%d.png' % (fn[:-4], n)); n += 1; cur, h = [], 0
    for b, im in items:
        if h + im.height > 1300: flush()
        cur.append((b, im)); h += im.height
    flush()
print(len(want), 'блоков')
