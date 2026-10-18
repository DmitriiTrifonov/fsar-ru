"""Write translations of whole-file texts (2D / EdoComment / Profile) into the table.
usage: set_ru_files.py <file.txt>     format: a line '=== <folder> <file name without .txt>' then the text (any lines, blank lines allowed)."""
import sys, csv, re, os
blocks = {}; cur = None
for line in open(sys.argv[1], encoding="utf-8").read().replace("\r\n", "\n").split("\n"):
    m = re.match(r"^=== (\S+) (\S+)\s*$", line)
    if m:
        cur = (m.group(1), m.group(2)); blocks[cur] = []
    elif cur is not None:
        blocks[cur].append(line)
rows = list(csv.reader(open("text/dialogue.csv", encoding="utf-8-sig")))
hdr, body = rows[0], rows[1:]; ci = hdr.index("Русский"); n = 0
for r in body:
    key = (r[0], r[1])
    if key in blocks and r[2] == "-":
        r[ci] = "\n".join(blocks[key]).strip("\n"); n += 1
csv.writer(open("text/dialogue.csv", "w", newline="", encoding="utf-8-sig")).writerows([hdr] + body)
print(f"{n} of {len(blocks)} files written")
import subprocess; subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), 'ru_sync.py'), 'export'])
