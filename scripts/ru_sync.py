"""Sync Russian cells between the local full table and the tracked text/ru.csv (chapter, scene, id, Russian only).
usage: ru_sync.py export   # text/dialogue.csv -> text/ru.csv   (run after edits; set_ru*.py do it themselves)
       ru_sync.py import   # text/ru.csv -> Русский column of text/dialogue.csv"""
import sys, csv
FULL, RU = "text/dialogue.csv", "text/ru.csv"


def export():
    rows = list(csv.reader(open(FULL, encoding="utf-8-sig")))
    ci = rows[0].index("Русский")
    out = [r[:3] + [r[ci]] for r in rows[1:] if r[ci].strip()]
    with open(RU, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n"); w.writerow(["Глава", "Сцена", "ID", "Русский"]); w.writerows(out)
    print(f"{len(out)} Russian rows -> {RU}")


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


if __name__ == "__main__":
    {"export": export, "import": import_}[sys.argv[1]]()
