"""Dump a chapter for proofreading: review_dump.py <chapter>
one line per distinct (ID, English): '[scene] ID speaker: English  =>  Русский'  (' / ' = line break). Read-only."""
import csv, re, sys
sys.path.insert(0, __import__("os").path.dirname(__file__))
FACES = {1: "Мондо", 2: "Кусаби", 3: "Крис", 4: "Питер", 5: "Эдо", 6: "Рок", 7: "Сью", 8: "Мати", 9: "Сестра", 10: "Мария", 11: "Пират", 12: "Эль-Крашер",
         13: "Яёи", 14: "Стефан", 15: "Сонни", 16: "Табс", 17: "Сётаро", 18: "Кай-отец", 19: "Юри", 20: "Сэйдзи", 21: "Кэн", 22: "Степ", 23: "Реми", 25: "Косси",
         27: "Такаока", 28: "Нацуко", 29: "Шот", 30: "Ритц", 31: "Медсестра", 32: "Морисима", 34: "Пугало", 35: "Пугало", 36: "Пугало"}
chap = sys.argv[1]
rows = [r for r in csv.reader(open("text/dialogue.csv", encoding="utf-8-sig")) if r[0] == chap]
seen = set(); scenes = []
for r in rows:
    if r[1] not in scenes: scenes.append(r[1])
norm = lambda t: " ".join(t.split())
for sc in scenes:
    face = {}
    try:
        t = open(f"decoded/Chapter/Pack/{chap}/{sc}.txt", "rb").read().decode("utf-16", errors="replace"); cur = None
        for m in re.finditer(r'<SETFACE2>\s*(\d+)|<TEXT_EX>\s*(\d+)', t):
            if m.group(1): cur = int(m.group(1))
            else: face.setdefault(int(m.group(2)), cur)
    except FileNotFoundError: pass
    out = []
    for r in rows:
        if r[1] != sc or not r[10].strip(): continue
        k = (r[2], norm(r[5]))
        if k in seen: continue
        seen.add(k)
        try: f = face.get(int(r[2].split("#")[0]))
        except ValueError: f = None
        sp = FACES.get(f, f"#{f}") if f is not None else "-"
        en = r[5] if r[5].strip() else "(JA) " + r[4]
        out.append(f"[{sc}] {r[2]} {sp}: {en.replace(chr(10), ' / ')}  =>  {r[10].replace(chr(10), ' / ')}")
    print("\n".join(out))
