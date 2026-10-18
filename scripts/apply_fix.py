"""Apply proofreading fixes: apply_fix.py <chapter> <fixfile> [--check]
fix lines: '[scene] ID new text'  (as in review_dump.py; '~' = forced break). The new text replaces the Russian cell of every row in the
chapter with the same ID and the same English text (so duplicated scenes stay in sync). Lines are re-wrapped to <=194 px / 3 lines."""
import csv, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(__file__))
import linewidth as L
MAXW, MAXL = 194, 3
font = L.font()


def wrap(text):
    out = []
    for part in text.split("~"):
        words = part.split()
        if not words: out.append(""); continue
        n = len(words); w = lambda i, j: L.width(" ".join(words[i:j]), font); best = None
        for k in range(1, MAXL + 1):
            INF = (10**9, 10**9); dp = [[INF] * (n + 1) for _ in range(k + 1)]; pv = [[0] * (n + 1) for _ in range(k + 1)]; dp[0][0] = (0, 0)
            for a in range(1, k + 1):
                for j in range(a, n + 1):
                    for i in range(a - 1, j):
                        if dp[a - 1][i] == INF: continue
                        x = w(i, j); c = (max(dp[a - 1][i][0], x), dp[a - 1][i][1] + x * x)
                        if c < dp[a][j]: dp[a][j] = c; pv[a][j] = i
            if dp[k][n] != INF and dp[k][n][0] <= MAXW:
                cuts = []; j = n
                for a in range(k, 0, -1): i = pv[a][j]; cuts.append((i, j)); j = i
                best = [" ".join(words[i:j]) for i, j in reversed(cuts)]; break
        out += best or [" ".join(words)]
    return "\n".join(out)


args = [a for a in sys.argv[1:] if not a.startswith("--")]; chap, path = args[:2]; CHECK = "--check" in sys.argv
rows = list(csv.reader(open("text/dialogue.csv", encoding="utf-8-sig"))); hdr, body = rows[0], rows[1:]
ci, ei = hdr.index("Русский"), hdr.index("English"); norm = lambda t: " ".join(t.split())
by_key = {(r[1], r[2]): r for r in body if r[0] == chap}
n = bad = missing = 0
for ln in open(path, encoding="utf-8").read().split("\n"):
    m = re.match(r"^\[(\S+)\] (\S+) (.*)$", ln.strip())
    if not m: continue
    sc, i, text = m.groups(); src = by_key.get((sc, i))
    if not src: print("нет такой строки:", sc, i); missing += 1; continue
    new = wrap(text.strip())
    if len(new.split("\n")) > MAXL or any(L.width(x, font) > MAXW for x in new.split("\n")):
        print("НЕ ВЛЕЗАЕТ:", sc, i, new.replace("\n", " / ")); bad += 1
    en = norm(src[ei])
    for r in body:
        if r[0] == chap and r[2] == i and norm(r[ei]) == en:
            r[ci] = new; n += 1
print(f"{n} ячеек {'проверено' if CHECK else 'исправлено'}, не влезает: {bad}, нет строки: {missing}")
if not CHECK:
    csv.writer(open("text/dialogue.csv", "w", newline="", encoding="utf-8-sig")).writerows([hdr] + body)
    subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), "ru_sync.py"), "export"])
