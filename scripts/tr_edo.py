"""Load EdoComment translations (Savefont, save screen): tr_edo.py text/ru/EdoComment.tr [--check]
lines: 'Name text' ('~' = forced line break; ½ is the sentence mark of the originals, break opportunity after it).
Wraps to <=178 px (widest original line is 187; in game 187 touches the window edge) by the Savefont advance sum."""
import csv, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(__file__))
import fontio
F = fontio.Font("patched_raw/2D/Savefont_Chiaro_12px_log8.NFTR"); LIMIT = 178


def limit_for(name):
    """Per-box width (widest original line: R_* 187, Title_* 122, SaveData* 181; checked in game: Title_* box is cut at the screen edge)."""
    return 128 if name.startswith("Title") else 170 if name.startswith("SaveData") else 178
CHECK = "--check" in sys.argv


def mw(t):
    tot = 0
    for i, ch in enumerate(t):
        gi = F.map.get(ord(ch))
        if gi is None: continue
        l, g, a = F.width(gi); tot += a if i < len(t) - 1 else max(g, a)
    return tot


def join(toks):
    s = ""
    for k, t in enumerate(toks):
        s += t
        if k < len(toks) - 1 and not t.endswith("½"): s += " "
    return s


def wrap(piece, LIMIT=LIMIT):
    if piece != piece.lstrip() or mw(piece.rstrip()) <= LIMIT:     # centred / short pieces stay as written
        return [piece]
    toks = [t for t in re.split(r"(?<=½)| ", piece) if t]
    n = len(toks); INF = (10**9, 10**9)
    for k in range(1, 40):
        dp = [[INF] * (n + 1) for _ in range(k + 1)]; pv = [[0] * (n + 1) for _ in range(k + 1)]; dp[0][0] = (0, 0)
        for a in range(1, k + 1):
            for j in range(a, n + 1):
                for i in range(a - 1, j):
                    if dp[a - 1][i] == INF: continue
                    x = mw(join(toks[i:j])); c = (max(dp[a - 1][i][0], x), dp[a - 1][i][1] + x * x)
                    if c < dp[a][j]: dp[a][j] = c; pv[a][j] = i
        if dp[k][n] != INF and dp[k][n][0] <= LIMIT:
            cuts = []; j = n
            for a in range(k, 0, -1): i = pv[a][j]; cuts.append((i, j)); j = i
            return [join(toks[i:j]) for i, j in reversed(cuts)]
    return [piece]


tr = {}
for ln in open([a for a in sys.argv[1:] if not a.startswith("--")][0], encoding="utf-8").read().split("\n"):
    if not ln.strip(): continue
    name, _, text = ln.partition(" ")
    tr[name] = "\n".join(x for p in text.split("~") for x in wrap(p, limit_for(name)))
rows = list(csv.reader(open("text/dialogue.csv", encoding="utf-8-sig"))); hdr, body = rows[0], rows[1:]; ci = hdr.index("Русский"); n = 0
for r in body:
    if r[0] == "EdoComment" and r[1] in tr: r[ci] = tr[r[1]]; n += 1
bad = [k for k, v in tr.items() if any(mw(x.rstrip()) > limit_for(k) for x in v.split("\n"))]
miss = sorted({c for v in tr.values() for c in v if ord(c) not in F.map and c != "\n"})
print(f"{len(tr)} в файле, {n} в таблице, не влезает: {bad}, нет в шрифте: {miss!r}")
if not CHECK:
    csv.writer(open("text/dialogue.csv", "w", newline="", encoding="utf-8-sig")).writerows([hdr] + body)
    subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), "ru_sync.py"), "export"])
