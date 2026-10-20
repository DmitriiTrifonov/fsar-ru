"""ru_changes.py [от] [до]: какие реплики text/ru.csv изменились между двумя ревизиями git.
Ревизии: тег, коммит, HEAD~5, ... (по умолчанию от = последний тег, до = рабочая копия).
Выводит таблицу «Глава | Сцена | ID | было | стало»; `--md` — Markdown, `--ids` — только сводка по сценам."""
import csv, io, subprocess, sys

def load(rev):
    if rev is None:
        text = open("text/ru.csv", encoding="utf-8-sig").read()
    else:
        text = subprocess.run(["git", "show", f"{rev}:text/ru.csv"], capture_output=True, text=True, check=True).stdout.lstrip("﻿")
    return {(r["Глава"], r["Сцена"], r["ID"]): r["Русский"] for r in csv.DictReader(io.StringIO(text))}

def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    md, ids = "--md" in sys.argv, "--ids" in sys.argv
    old_rev = args[0] if args else subprocess.run(["git", "describe", "--tags", "--abbrev=0"], capture_output=True, text=True, check=True).stdout.strip()
    new_rev = args[1] if len(args) > 1 else None
    old, new = load(old_rev), load(new_rev)
    flat = lambda s: s.replace("\n", " ")
    changed = [(k, old.get(k), new.get(k)) for k in sorted(set(old) | set(new)) if old.get(k) != new.get(k)]
    print(f"# {old_rev} -> {new_rev or 'рабочая копия'}: изменено {len(changed)}", file=sys.stderr)
    if ids:
        by = {}
        for k, _, _ in changed: by.setdefault((k[0], k[1]), []).append(k[2])
        for (c, s), l in by.items(): print(f"{c} {s}: {len(l)} ({', '.join(l)})")
        return
    for (c, s, i), a, b in changed:
        a = "(нет)" if a is None else flat(a); b = "(нет)" if b is None else flat(b)
        print(f"| {c} | {s} | {i} | {a} | {b} |" if md else f"{c} {s} {i}\n  было:  {a}\n  стало: {b}")

main()
