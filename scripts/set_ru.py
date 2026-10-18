"""Write Russian translations into the table: set_ru.py <chapter> <scene> <file.txt>
file format: blocks separated by a blank line, first line = ID, following lines = the translated text (line breaks kept)."""
import sys, csv, os
chap, scene, path = sys.argv[1:4]
blocks = [b for b in open(path, encoding="utf-8").read().replace("\r\n", "\n").split("\n\n") if b.strip()]
tr = {}
for b in blocks:
    lines = b.strip("\n").split("\n"); tr[lines[0].strip()] = "\n".join(lines[1:])
rows = list(csv.reader(open("text/dialogue.csv", encoding="utf-8-sig")))
hdr, body = rows[0], rows[1:]; ci = hdr.index("Русский"); n = 0
for r in body:
    if r[0] == chap and r[1] == scene and r[2] in tr:
        r[ci] = tr[r[2]]; n += 1
csv.writer(open("text/dialogue.csv", "w", newline="", encoding="utf-8-sig")).writerows([hdr] + body)
print(f"{n} of {len(tr)} entries written for {chap}/{scene}")
import subprocess; subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), 'ru_sync.py'), 'export'])
