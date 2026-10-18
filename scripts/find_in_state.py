"""Find dialogue strings from the table in a melonDS savestate / RAM dump. usage: find_in_state.py FILE [BASE_OFFSET]"""
import sys, csv, re
import os
d = open(sys.argv[1], "rb").read()
limit = int(os.environ.get("LIMIT", len(d)))
d = d[:limit]
base = int(sys.argv[2], 0) if len(sys.argv) > 2 else 0
rows = list(csv.reader(open("text/dialogue.csv", encoding="utf-8-sig")))[1:]
pat = {}
for r in rows:
    for col, lang in (((5, "en"),) if os.environ.get("EN_ONLY") else ((5, "en"), (4, "ja"), (6, "fr"), (7, "de"), (8, "es"), (9, "it"))):
        for ln in r[col].split("\n"):
            ln = ln.strip()
            if len(ln) >= 10:
                pat.setdefault(ln.encode("utf-16le"), []).append((r[0], r[1], r[2], lang))
hits = []
for k, v in pat.items():
    i = d.find(k)
    while i >= 0:
        hits.append((i, k.decode("utf-16le"), v[0])); i = d.find(k, i + 2)
hits.sort()
print(len(hits), "hits")
for i, t, v in hits[:int(sys.argv[3]) if len(sys.argv) > 3 else 40]:
    print(hex(i), hex(i - base), v, repr(t))
