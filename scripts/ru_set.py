"""Edit one Russian reply everywhere at once: ru_set.py <chapter> <scene> <ID> "<text>"   (\\n in the text = line break)
Writes text/dialogue.csv, then ru_sync.py export (text/ru.csv, drafts text/ru/Cxx.tr). Run insert.py / build_rom.py afterwards."""
import sys, csv, os, subprocess
chap, scene, rid, text = sys.argv[1:5]
text = text.replace("\\n", "\n")
rows = list(csv.reader(open("text/dialogue.csv", encoding="utf-8-sig")))
hdr, body = rows[0], rows[1:]; ci = hdr.index("Русский"); n = 0
for r in body:
    if (r[0], r[1], r[2]) == (chap, scene, rid): r[ci] = text; n += 1
if n != 1: sys.exit(f"{chap}/{scene}/{rid}: найдено строк {n}, ожидалась 1")
csv.writer(open("text/dialogue.csv", "w", newline="", encoding="utf-8-sig")).writerows([hdr] + body)
subprocess.run([sys.executable, "-I", os.path.join(os.path.dirname(__file__), "ru_sync.py"), "export"], check=True)
