"""Sync Russian cells between the local full table and the tracked text/ru.csv (chapter, scene, id, Russian only).
usage: ru_sync.py export   # text/dialogue.csv -> text/ru.csv   (run after edits; set_ru*.py do it themselves)
       ru_sync.py import   # text/ru.csv -> Русский column of text/dialogue.csv
       ru_sync.py tr       # text/ru.csv -> lines of text/ru/Cxx.tr drafts (export and import do it themselves)
       ru_sync.py check    # list drafts that differ from text/ru.csv, change nothing
text/ru.csv is the source of truth; the .tr drafts only follow it."""
import sys, csv, os, re, glob
FULL, RU = "text/dialogue.csv", "text/ru.csv"


def export():
    rows = list(csv.reader(open(FULL, encoding="utf-8-sig")))
    ci = rows[0].index("Русский")
    out = [r[:3] + [r[ci]] for r in rows[1:] if r[ci].strip()]
    with open(RU, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n"); w.writerow(["Глава", "Сцена", "ID", "Русский"]); w.writerows(out)
    print(f"{len(out)} Russian rows -> {RU}")
    sync_tr()


def _norm(t):
    return re.sub(r"\s+", " ", t.replace("~", " ")).strip()


def sync_tr(write=True):
    """Bring the text of every line of text/ru/{Cxx,Common}.tr in line with text/ru.csv (compared ignoring line breaks)."""
    ru = {tuple(r[:3]): r[3] for r in list(csv.reader(open(RU, encoding="utf-8")))[1:]}
    by_id = {(k[0], k[2]): v for k, v in ru.items()}
    total = 0
    for path in sorted(glob.glob("text/ru/*.tr")):
        m = re.match(r"(C\d\d|Common)", os.path.basename(path))
        if not m: continue
        chap = m.group(1); scene = None; out = []; n = 0
        for ln in open(path, encoding="utf-8").read().split("\n"):
            h = re.match(r"^=== (?:(\S+) )?(\S+)\s*$", ln)
            if h:
                if h.group(1): chap = h.group(1)
                scene = h.group(2)
                if scene.endswith("_*"): chap, scene = scene[:-2], "*"
            elif ln.strip():
                i, _, old = ln.partition(" ")
                v = ru.get((chap, scene, i), by_id.get((chap, i)))
                if v is not None and _norm(v) != _norm(old):
                    ln = i + " " + (v.replace("\n", "~") if "~" in old else " ".join(v.split()))
                    n += 1
                    if not write: print(f"{path}: {i}")
            out.append(ln)
        if n and write:
            open(path, "w", encoding="utf-8").write("\n".join(out))
        total += n
    print(f"{total} lines of text/ru/*.tr {'updated' if write else 'differ from text/ru.csv'}")


def import_():
    ru = {tuple(r[:3]): r[3] for r in list(csv.reader(open(RU, encoding="utf-8")))[1:]}
    rows = list(csv.reader(open(FULL, encoding="utf-8-sig")))
    ci = rows[0].index("Русский"); n = 0
    for r in rows[1:]:
        v = ru.get(tuple(r[:3]))
        if v is not None and r[ci] != v:
            r[ci] = v; n += 1
    csv.writer(open(FULL, "w", newline="", encoding="utf-8-sig")).writerows(rows)
    print(f"{n} cells updated from {RU}")
    sync_tr()


if __name__ == "__main__":
    {"export": export, "import": import_, "tr": sync_tr, "check": lambda: sync_tr(False)}[sys.argv[1]]()
