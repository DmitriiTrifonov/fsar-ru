"""Insert translated text from the table back into the game scripts.

usage: insert.py [--csv text/dialogue.csv] [--col Русский] [--lang ue]

For every row whose cell in --col is non-empty and differs from the current text, the matching
entry in decoded/Chapter/Pack/<chapter>/<lang>/<scene>.s is rewritten and the file is written to
patched/ (same relative path). decoded/ stays pristine. build_rom.py prefers patched/ over decoded/.
"""
import argparse, csv, os, sys, collections
sys.path.insert(0, os.path.dirname(__file__))
import scriptfmt as S

ap = argparse.ArgumentParser()
ap.add_argument("--csv", default="text/dialogue.csv")
ap.add_argument("--col", default="Русский")
ap.add_argument("--lang", default="ue")
a = ap.parse_args()

ROOT = "decoded/Chapter/Pack"


def split_body(body):
    """-> (head_lines, text_lines, tail_lines, inner_comments). Text lines exclude <R> markers."""
    lines = body.split("\r\n")
    idx = [i for i, l in enumerate(lines) if l and not l.startswith("//")]
    if not idx:
        return lines, [], [], False
    f, l = idx[0], idx[-1]
    inner = any(x.startswith("//") for x in lines[f:l + 1])
    text = [x for x in lines[f:l + 1] if x != "<R>" and not x.startswith("//")]
    return lines[:f], text, lines[l + 1:], inner


def make_body(head, text, tail):
    return "\r\n".join(head + ["\r\n<R>\r\n".join(text)] + tail)


rows = list(csv.reader(open(a.csv, encoding="utf-8-sig")))
hdr, rows = rows[0], rows[1:]
ci = hdr.index(a.col)
by_file = collections.defaultdict(dict)
for r in rows:
    if r[ci].strip():
        by_file[(r[0], r[1])][r[2]] = r[ci].replace("\r\n", "\n")

RAW_DIRS = ("2D", "EdoComment", "Profile")      # plain UTF-16 .txt files: whole file = one entry with ID "-"


def insert_raw(chap, scene, text):
    src = f"extracted/data/{chap}/{a.lang}/{scene}.txt"
    if not os.path.exists(src):
        return 0
    orig = open(src, "rb").read().decode("utf-16")
    core = orig.strip("\r\n")
    lead = orig[:len(orig) - len(orig.lstrip("\r\n"))]
    tail = orig[len(orig.rstrip("\r\n")):]
    new = lead + text.strip("\n").replace("\n", "\r\n") + tail
    if new == orig:
        return 0
    dst = f"patched_raw/{chap}/{a.lang}/{scene}.txt"
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    open(dst, "wb").write(new.encode("utf-16"))
    return 1


changed = files = 0
for (chap, scene), cells in sorted(by_file.items()):
    if chap in RAW_DIRS:
        n = insert_raw(chap, scene, cells["-"]) if "-" in cells else 0
        changed += n; files += n
        continue
    src = f"{ROOT}/{chap}/{a.lang}/{scene}.s"
    if not os.path.exists(src):
        continue
    head, entries = S.parse(S.read_s(src))
    out, touched, seen = [], 0, {}
    for i, body in entries:
        if i:
            seen[i] = seen.get(i, 0) + 1
            i_key = i if seen[i] == 1 else f"{i}#{seen[i]}"
        else:
            i_key = i
        if i_key in cells:
            h, text, tail, inner = split_body(body)
            new = [x for x in cells[i_key].split("\n")]
            if new != text:
                if inner:
                    print(f"warning: comment lines inside text, dropped: {chap}/{scene} {i}")
                body = make_body(h, new, tail); touched += 1
        out.append((i, body))
    if touched:
        dst = f"patched/Chapter/Pack/{chap}/{a.lang}/{scene}.s"
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        open(dst, "wb").write(S.build(head, out).encode("utf-16"))   # utf-16 = BOM + LE
        changed += touched; files += 1
print(f"{changed} entries changed in {files} files")
