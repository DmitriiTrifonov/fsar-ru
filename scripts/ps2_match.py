"""PS2: сопоставление строк блоков сцен (английский образ) с репликами таблицы DS.

Глифы в атласе PS2 — по одному на уникальный символ сцены, поэтому «отпечаток» строки (номер
первого вхождения каждого символа, без пробелов) совпадает с отпечатком английской реплики DS.
Неоднозначные совпадения разрешаются непрерывностью (следующий ID той же сцены).
Вывод: text/ps2/map.tsv (файл, блок, строка, сцена, ID) — английского текста там нет.

  python3 -I scripts/ps2_match.py <en/DATA/EVENT> <jp/DATA/EVENT> [text/ps2/map.tsv]
Столбец «яп_без_перевода» = 1, если строка в английском образе не отличается от японской
(не переведена, совпадение с DS случайное — игнорировать).
"""
import collections
import csv
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
from ps2_scene import SPACE, parse_container, parse_scene


def canon(seq):
    m = {}
    return tuple(m.setdefault(x, len(m)) for x in seq)


def norm(t):
    t = (t.replace('…', '...').replace('’', "'").replace('‘', "'")
          .replace('“', '"').replace('”', '"'))
    return re.sub(r'\s+', '', t)


def load_ds(path='text/dialogue.csv'):
    rows = [r for r in csv.DictReader(open(path, encoding='utf-8-sig')) if re.match(r'C\d\d$', r['Глава'])]
    idx = collections.defaultdict(list)
    for n, r in enumerate(rows):
        idx[canon(norm(r['English']))].append(n)
    return rows, idx


def resolve(cands):
    """cands[i] = список порядковых номеров строк DS; Витерби: бонус за следующий номер подряд."""
    NONE = -1
    prev = {NONE: (0, None)}
    hist = []
    for c in cands:
        opts = list(c) + [NONE]
        cur = {}
        for o in opts:
            best = None
            for p, (sc, _) in prev.items():
                s = sc + (-0.5 if o == NONE else 0) + (1 if (p != NONE and o != NONE and o == p + 1) else 0)
                if best is None or s > best[0]:
                    best = (s, p)
            cur[o] = best
        hist.append(cur)
        prev = cur
    o = max(prev, key=lambda k: prev[k][0])
    out = []
    for cur in reversed(hist):
        out.append(o)
        o = cur[o][1]
    return out[::-1]


def main():
    base = sys.argv[1]
    jpbase = sys.argv[2]
    outp = sys.argv[3] if len(sys.argv) > 3 else 'text/ps2/map.tsv'
    rows, idx = load_ds()
    res = []
    stat = collections.Counter()
    for f in sorted(os.listdir(base)):
        if not f.endswith('.BIN') or f in ('GDB.BIN', 'R00.BIN'):
            continue
        d = open(os.path.join(base, f), 'rb').read()
        dj = open(os.path.join(jpbase, f), 'rb').read()
        ej = parse_container(dj)
        for k, (s, z) in enumerate(parse_container(d)):
            try:
                sc = parse_scene(d[s * 2048:s * 2048 + z])
            except Exception:
                continue
            if not sc['nlines']:
                continue
            sj = parse_scene(dj[ej[k][0] * 2048:ej[k][0] * 2048 + ej[k][1]])
            cands = []
            for ln in sc['lines']:
                g = [x for r in ln['rows'] for x in r if x != SPACE]
                cands.append(idx.get(canon(g), []))
            for i, o in enumerate(resolve(cands)):
                if o < 0:
                    stat['none'] += 1
                    res.append((f, k, i, '', '', len(cands[i]), 0))
                else:
                    stat['uniq' if len(cands[i]) == 1 else 'multi'] += 1
                    r = rows[o]
                    jps = int(sj['lines'][i]['rows'] == sc['lines'][i]['rows'])
                    res.append((f, k, i, r['Сцена'], r['ID'], len(cands[i]), jps))
    os.makedirs(os.path.dirname(outp), exist_ok=True)
    with open(outp, 'w', encoding='utf-8') as fh:
        fh.write('файл\tблок\tстрока\tсцена\tID\tкандидатов\tяп_без_перевода\n')
        for r in res:
            fh.write('\t'.join(map(str, r)) + '\n')
    print(stat)


if __name__ == '__main__':
    main()
