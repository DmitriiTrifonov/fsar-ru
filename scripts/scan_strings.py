"""List printable strings in arm9.bin / overlays: ASCII and UTF-16LE. usage: scan_strings.py [min_len]"""
import sys, re, glob, os
MIN = int(sys.argv[1]) if len(sys.argv) > 1 else 4
files = ["extracted/arm9.bin"] + sorted(glob.glob("extracted/overlay/*.bin")) + ["extracted/arm7.bin"]
a_re = re.compile(rb"[\x20-\x7e]{%d,}" % MIN)
u_re = re.compile(rb"(?:[\x20-\x7e]\x00){%d,}" % MIN)
for f in files:
    d = open(f, "rb").read()
    a = [(m.start(), m.group().decode()) for m in a_re.finditer(d)]
    u = [(m.start(), m.group().decode("utf-16le")) for m in u_re.finditer(d)]
    print(f"== {os.path.basename(f)}  size {len(d)}  ascii {len(a)}  utf16 {len(u)}")
    if "--dump" in sys.argv:
        out = open(f"build/strings_{os.path.basename(f)}.txt", "w")
        for off, t in a: out.write(f"A {off:06x} {t}\n")
        for off, t in u: out.write(f"U {off:06x} {t}\n")
