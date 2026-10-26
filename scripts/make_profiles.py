"""Профили персонажей: make_profiles.py [Имя ...]
Пишет text/chars/<Имя>.md. Блок между <!-- auto --> и <!-- /auto --> перегенерируется (русские реплики, главы,
слова-маркеры обращений); остальное — ручные разделы, они сохраняются. Английский текст в профили не попадает (в git)."""
import csv, re, sys, os, collections
FACES = {1: "Мондо", 2: "Кусаби", 3: "Крис", 4: "Питер", 5: "Эдо", 6: "Рок", 7: "Сью", 8: "Мати", 9: "Сестра", 10: "Мария", 11: "Пират", 12: "Эль-Крашер",
         13: "Яёи", 14: "Стефан", 15: "Сонни", 16: "Табс", 17: "Сётаро", 18: "Кай-отец", 19: "Юри", 20: "Сэйдзи", 21: "Кэн", 22: "Степ", 23: "Реми", 25: "Косси",
         27: "Такаока", 28: "Нацуко", 29: "Шот", 30: "Ритц", 31: "Медсестра", 32: "Морисима", 34: "Пугало", 35: "Пугало", 36: "Пугало"}
MANUAL = """## Кто это

## Голос

## Обращения
(таблица ты/вы — в `text/STYLE.md`; здесь исключения и нюансы)

## Термины и имена

## Решения

## Эталонные реплики
"""
ru = {(r[0], r[1], r[2]): r[3] for r in csv.reader(open("text/ru.csv", encoding="utf-8-sig")) if len(r) > 3}
src = list(csv.reader(open("text/dialogue.csv", encoding="utf-8-sig")))[1:]
by = collections.defaultdict(list)  # имя -> [(гл, сцена, id, текст)]
cache = {}
def faces(chap, sc):
    if (chap, sc) in cache: return cache[chap, sc]
    face = {}
    try:
        t = open(f"decoded/Chapter/Pack/{chap}/{sc}.txt", "rb").read().decode("utf-16", errors="replace"); cur = None
        for m in re.finditer(r'<SETFACE2>\s*(\d+)|<TEXT_EX>\s*(\d+)', t):
            if m.group(1): cur = int(m.group(1))
            else: face.setdefault(int(m.group(2)), cur)
    except FileNotFoundError: pass
    cache[chap, sc] = face; return face
for r in src:
    t = ru.get((r[0], r[1], r[2]), "").strip()
    if not t: continue
    try: f = faces(r[0], r[1]).get(int(r[2].split("#")[0]))
    except ValueError: f = None
    if f in FACES: by[FACES[f]].append((r[0], r[1], r[2], t.replace("\n", " / ")))
MARK = [("месье", r"[Мм]есье"), ("мистер", r"[Мм]истер"), ("ты-формы", r"\b(ты|тебя|тебе|твой|твоя|тво[ёе]|тебя)\b"),
        ("вы-формы", r"\b(вы|вас|вам|ваш|ваша|ваше|ваши)\b"), ("«ик»", r"\b[Ии]к\b")]
def auto(name, rows):
    ch = collections.Counter(r[0] for r in rows)
    o = [f"Реплик: {len(rows)}. Главы: " + ", ".join(f"{c} ({n})" for c, n in sorted(ch.items())) + "."]
    o.append("Маркеры: " + "; ".join(f"{k} {sum(1 for r in rows if re.search(p, r[3]))}" for k, p in MARK) + ".")
    o.append("\n### Реплики\n")
    for c, s, i, t in rows: o.append(f"- {s} {i}: {t}")
    return "\n".join(o)
names = sys.argv[1:] or sorted(by)
os.makedirs("text/chars", exist_ok=True)
for n in names:
    if n not in by: print("нет реплик:", n); continue
    p = f"text/chars/{n}.md"; blk = f"<!-- auto -->\n{auto(n, by[n])}\n<!-- /auto -->"
    if os.path.exists(p):
        old = open(p, encoding="utf-8").read()
        new = re.sub(r"<!-- auto -->.*<!-- /auto -->", lambda m: blk, old, flags=re.S)
    else:
        new = f"# {n}\n\n{MANUAL}\n## Реплики (авто)\n{blk}\n"
    open(p, "w", encoding="utf-8").write(new); print(n, len(by[n]))
