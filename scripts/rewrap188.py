"""Re-break Russian replies so no line is wider than LIMIT px (left-portrait window clips at ~188 px, measured 2026-10-26).
Only line breaks change, never words. usage: rewrap188.py [--limit 188] [--apply]   (without --apply: report only)
Replies that cannot be fixed by re-breaking within 3 lines are listed for manual shortening."""
import csv, sys, os, itertools, subprocess
sys.path.insert(0, os.path.dirname(__file__))
import linewidth
limit = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else 188
apply = "--apply" in sys.argv
W = linewidth.width

def best_break(words, n):
    """n lines, minimal max width (ties: minimal sum of squares); None if impossible"""
    best = None
    for cuts in itertools.combinations(range(1, len(words)), n - 1):
        parts = [" ".join(words[a:b]) for a, b in zip((0,) + cuts, cuts + (len(words),))]
        ws = [W(p) for p in parts]
        key = (max(ws), sum(w * w for w in ws))
        if best is None or key < best[0]: best = (key, parts)
    return best

rows = list(csv.reader(open("text/dialogue.csv", encoding="utf-8-sig")))
hdr, body = rows[0], rows[1:]; ci = hdr.index("Русский")
fixed, manual = [], []
for r in body:
    t = r[ci]
    if r[2] == "-" or not t: continue
    lines = t.split("\n")
    if max(W(l) for l in lines) <= limit: continue
    words = t.replace("\n", " ").split(" ")
    done = None
    for n in range(len(lines), 4):
        if n > len(words): break
        b = best_break(words, n)
        if b and b[0][0] <= limit: done = "\n".join(b[1]); break
    if done is None: manual.append((r[0], r[1], r[2], t)); continue
    fixed.append((r[0], r[1], r[2], t, done)); r[ci] = done
print(f"to fix: {len(fixed) + len(manual)}, re-broken: {len(fixed)}, manual: {len(manual)}")
for m in manual: print("MANUAL", m[:3], m[3].replace("\n", " / "), [W(l) for l in m[3].split("\n")])
if apply:
    csv.writer(open("text/dialogue.csv", "w", newline="", encoding="utf-8-sig")).writerows([hdr] + body)
    subprocess.run([sys.executable, "-I", os.path.join(os.path.dirname(__file__), "ru_sync.py"), "export"], check=True)
