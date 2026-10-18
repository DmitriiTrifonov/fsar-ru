"""Check the Russian column of the dialogue table against the dialogue-window limits.
usage: check_table.py [--csv text/dialogue.csv] [--col Русский] [--max-width 194] [--max-lines 3] [--show 15]
Limits measured in melonDS (2026-10-15): the game does NOT wrap or clip nicely; text starts at x=10 and must end
before the red border at x~207 (=> 194 px by linewidth.width); more than 3 lines scrolls the window."""
import argparse, csv, os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
import linewidth as L
import fontio


def menu_width(t, f):
    """Width of text drawn by menu code: pitch == advance, last glyph counts by its ink."""
    tot = 0
    for i, ch in enumerate(t):
        gi = f.map.get(ord(ch))
        if gi is None:
            continue
        left, gw, adv = f.width(gi)
        tot += adv if i < len(t) - 1 else max(gw, adv)
    return tot


ap = argparse.ArgumentParser()
ap.add_argument("--csv", default="text/dialogue.csv")
ap.add_argument("--col", default="Русский")
ap.add_argument("--max-width", type=int, default=194)
ap.add_argument("--max-lines", type=int, default=3)
ap.add_argument("--show", type=int, default=15)
a = ap.parse_args()

rows = list(csv.reader(open(a.csv, encoding="utf-8-sig")))
hdr, rows = rows[0], rows[1:]
ci = hdr.index(a.col)
ix_en = hdr.index("English")
RAW_DIRS = ("2D", "EdoComment", "Profile")
font = L.font()
bad, n = [], 0
for r in rows:
    t = r[ci]
    if not t.strip():
        continue
    n += 1
    ls = t.split("\n"); probs = []
    if r[0] == "Profile" and re.fullmatch(r"(profile|juckin)_\d\d", r[1]):
        # character profiles are drawn with Savefont, pitch == advance (no letter spacing); the text area right of the
        # portrait is ~125 px (the widest English line is 119)
        sv = fontio.Font("patched_raw/2D/Savefont_Chiaro_12px_log8.NFTR")
        for l in ls:
            w = menu_width(l.rstrip(), sv)
            if w > 125:
                probs.append(f"шире 125 px на {w - 125} ({w}): {l!r}")
            miss = sorted({c for c in l if ord(c) not in sv.map})
            if miss:
                probs.append(f"нет в шрифте: {''.join(miss)!r}")
        if probs:
            bad.append((r[0], r[1], r[2], probs))
        continue
    if r[0] == "EdoComment":
        # save-screen comments: Savefont, pitch == advance; widest original line is 187 px
        sv = fontio.Font("patched_raw/2D/Savefont_Chiaro_12px_log8.NFTR")
        for l in ls:
            w = menu_width(l.rstrip(), sv)
            lim = 128 if r[1].startswith("Title") else 170 if r[1].startswith("SaveData") else 178
            if w > lim:
                probs.append(f"шире {lim} px на {w - lim} ({w}): {l!r}")
            miss = sorted({c for c in l if ord(c) not in sv.map})
            if miss:
                probs.append(f"нет в шрифте: {''.join(miss)!r}")
        if probs:
            bad.append((r[0], r[1], r[2], probs))
        continue
    if r[0] in RAW_DIRS:
        # whole-file texts: widths unknown, compare with the widest English line of the same file (+15 %, +6 px)
        TAG = re.compile(r"\{[^}]*\}")        # control tags such as {color,1} are not drawn
        en_w = max((L.width(TAG.sub("", x).rstrip(), L.font("extracted/data/Chapter/Pack/Common/font.nftr")) for x in r[ix_en].split("\n")), default=0)
        lim = int(en_w * 1.15) + 6
        for l in ls:
            w = L.width(TAG.sub("", l).rstrip(), font)
            if w > lim:
                probs.append(f"шире английского на {w - en_w} px ({w} > лимит {lim}): {l!r}")
            miss = sorted({c for c in l if ord(c) not in font.map and not l.startswith("{")})
            if miss:
                probs.append(f"нет в шрифте: {''.join(miss)!r}")
        if probs:
            bad.append((r[0], r[1], r[2], probs))
        continue
    if len(ls) > a.max_lines:
        probs.append(f"{len(ls)} строк (макс. {a.max_lines})")
    for l in ls:
        w = L.width(l, font)
        if w > a.max_width:
            probs.append(f"шире на {w - a.max_width} px ({w}): {l!r}")
        miss = sorted({c for c in l if ord(c) not in font.map})
        if miss:
            probs.append(f"нет в шрифте: {''.join(miss)!r}")
    if probs:
        bad.append((r[0], r[1], r[2], probs))
print(f"проверено реплик: {n}, с проблемами: {len(bad)}")
for ch, sc, i, probs in bad[:a.show]:
    print(f"  {ch}/{sc} {i}: " + "; ".join(probs))
sys.exit(1 if bad else 0)
