"""Load drafts written as plain text with automatic wrapping: tr_bulk.py text/ru/C02.tr
format:  '=== C02_01' header (scene of the chapter given in the file name, or '=== C02 C02_01'), then one reply per line:
'ID text'. '~' in text forces a line break. Lines are balanced to <=188 px, <=3 lines; problems are reported.
Writes the Russian column of text/dialogue.csv and re-exports text/ru.csv."""
import csv, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(__file__))
import linewidth as L
MAXW, MAXL = 188, 3
font = L.font()


def wrap(text):
    out = []
    for part in text.split("~"):
        words = part.split()
        if not words:
            out.append(""); continue
        n = len(words)
        w = lambda i, j: L.width(" ".join(words[i:j]), font)
        best = None
        for k in range(1, MAXL + 1):
            # dp over splits into exactly k lines minimizing the widest line, then sum of squares
            INF = (10**9, 10**9)
            dp = [[INF] * (n + 1) for _ in range(k + 1)]; prev = [[0] * (n + 1) for _ in range(k + 1)]
            dp[0][0] = (0, 0)
            for a in range(1, k + 1):
                for j in range(a, n + 1):
                    for i in range(a - 1, j):
                        if dp[a - 1][i] == INF: continue
                        x = w(i, j)
                        c = (max(dp[a - 1][i][0], x), dp[a - 1][i][1] + x * x)
                        if c < dp[a][j]: dp[a][j] = c; prev[a][j] = i
            if dp[k][n] != INF and dp[k][n][0] <= MAXW:
                cuts = []; j = n
                for a in range(k, 0, -1):
                    i = prev[a][j]; cuts.append((i, j)); j = i
                best = [" ".join(words[i:j]) for i, j in reversed(cuts)]; break
        if best is None:
            best = [" ".join(words)]
        out += best
    return "\n".join(out)


CHECK = "--check" in sys.argv          # validate only: do not touch the table
path = [a for a in sys.argv[1:] if not a.startswith("--")][0]
m = re.match(r"(C\d\d|Common)", os.path.basename(path)); default_chap = m.group(1) if m else None
tr = {}; chap = default_chap; scene = None
for ln in open(path, encoding="utf-8").read().replace("\r\n", "\n").split("\n"):
    if not ln.strip(): continue
    h = re.match(r"^=== (?:(\S+) )?(\S+)\s*$", ln)
    if h:
        if h.group(1): chap = h.group(1)
        scene = h.group(2)
        if scene.endswith("_*"): chap, scene = scene[:-2], "*"      # '=== C14_*': by ID for every scene of the chapter
        continue
    i, _, text = ln.partition(" ")
    tr[(chap, scene, i)] = wrap(text.strip())
rows = list(csv.reader(open("text/dialogue.csv", encoding="utf-8-sig")))
hdr, body = rows[0], rows[1:]; ci = hdr.index("Русский"); n = 0; seen = set()
for r in body:
    k = (r[0], r[1], r[2])
    if k not in tr: k = (r[0], "*", r[2])
    if k in tr:
        r[ci] = tr[k]; n += 1; seen.add(k)
if not CHECK:
    csv.writer(open("text/dialogue.csv", "w", newline="", encoding="utf-8-sig")).writerows([hdr] + body)
for k in tr:
    if k not in seen: print("нет в таблице:", k)
bad = [(k, v) for k, v in tr.items() if len(v.split("\n")) > MAXL or any(L.width(x, font) > MAXW for x in v.split("\n"))]
for k, v in bad: print("НЕ ВЛЕЗАЕТ:", k, v.replace("\n", " / "))
print(f"{n} {'проверено' if CHECK else 'записано'}, {len(bad)} не влезает")
if CHECK:
    left = [(r[1], r[2]) for r in body if r[0] == default_chap and not r[ci].strip() and r[hdr.index("English")].strip()]
    print(f"ещё без перевода (с английским текстом): {len(left)}", left[:15])
    sys.exit(0)
subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), "ru_sync.py"), "export"])
