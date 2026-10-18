"""Compact dump of untranslated replies for translating: dump_scene.py <chapter> [scene ...] [--all]
prints '=== scene' then 'ID speaker: English' (line breaks of the original are shown as ' / ')."""
import csv, re, sys
FACES = {1: "Мондо", 2: "Кусаби", 3: "Крис", 4: "Питер", 5: "Эдо", 6: "Рок", 7: "Сью", 8: "Мати", 9: "Сестра", 10: "Мария", 11: "Пират", 12: "Эль-Крашер",
         13: "Яёи", 14: "Стефан", 15: "Сонни", 16: "Табс", 17: "Сётаро", 18: "Кай-отец", 19: "Юри", 20: "Сэйдзи", 21: "Кэн", 22: "Степ", 23: "Реми", 25: "Косси",
         27: "Такаока", 28: "Нацуко", 29: "Шот", 30: "Ритц", 31: "Медсестра", 32: "Морисима", 34: "Пугало", 35: "Пугало", 36: "Пугало"}
args = [a for a in sys.argv[1:] if not a.startswith("--")]
show_all = "--all" in sys.argv
chap, only = args[0], set(args[1:])
rows = [r for r in csv.reader(open("text/dialogue.csv", encoding="utf-8-sig")) if r[0] == chap]
scenes = []
for r in rows:
    if r[1] not in scenes: scenes.append(r[1])
for sc in scenes:
    if only and sc not in only: continue
    rs = [r for r in rows if r[1] == sc and (show_all or not r[10].strip())]
    if not rs: continue
    path = f"decoded/Chapter/Pack/{chap}/{sc}.txt"
    face = {}
    try:
        t = open(path, "rb").read().decode("utf-16", errors="replace"); cur = None
        for m in re.finditer(r'<SETFACE2>\s*(\d+)|<TEXT_EX>\s*(\d+)', t):
            if m.group(1): cur = int(m.group(1))
            else: face.setdefault(int(m.group(2)), cur)
    except FileNotFoundError:
        pass
    print(f"=== {sc} ({len(rs)})")
    for r in rs:
        try: f = face.get(int(r[2].split("#")[0]))
        except ValueError: f = None
        sp = FACES.get(f, f"#{f}") if f is not None else "-"
        print(f"{r[2]} {sp}: " + r[5].replace("\n", " / "))
