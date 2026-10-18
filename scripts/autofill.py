"""Fill untranslated rows of a chapter whose English text is identical to already translated rows elsewhere
(only when all those translations agree and the English is >= 10 chars): autofill.py <chapter> [--dry]"""
import csv, subprocess, sys, os, collections
chap = sys.argv[1]; dry = "--dry" in sys.argv
rows = list(csv.reader(open("text/dialogue.csv", encoding="utf-8-sig")))
hdr, body = rows[0], rows[1:]; ci = hdr.index("Русский"); ei = hdr.index("English")
norm = lambda t: " ".join(t.split())          # ignore line-break differences
m = collections.defaultdict(set); cnt = collections.Counter()
for r in body:
    if r[ci].strip() and r[ei].strip(): m[norm(r[ei])].add(norm(r[ci])); cnt[(norm(r[ei]), r[ci])] += 1
n = 0
for r in body:
    k = norm(r[ei])
    if r[0] == chap and not r[ci].strip() and len(k) >= 10 and len(m.get(k, ())) == 1:
        r[ci] = max((c for (e, c) in cnt if e == k), key=lambda c: cnt[(k, c)]); n += 1
print(f"{n} rows filled from identical English")
if not dry:
    csv.writer(open("text/dialogue.csv", "w", newline="", encoding="utf-8-sig")).writerows([hdr] + body)
    subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), "ru_sync.py"), "export"])
