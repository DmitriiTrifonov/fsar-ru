"""Build a Cyrillic version of an NFTR font (default: the main dialogue font).

Latin-look-alike letters reuse existing glyphs (extra code points -> same glyph index).
The other 44 letters are drawn here (pixel art, same 1px-stroke style) and written over glyph
slots that English text never uses (accented Latin-1 letters). CMAP is extended, file grows a few bytes.

usage: make_ru_font.py [SRC.nftr] [OUT.nftr]
"""
import sys, os, struct, glob, re, collections
sys.path.insert(0, os.path.dirname(__file__))
import fontio, scriptfmt as S

SRC = sys.argv[1] if len(sys.argv) > 1 else "extracted/data/Chapter/Pack/Common/font.nftr"
OUT = sys.argv[2] if len(sys.argv) > 2 else "patched_raw/Chapter/Pack/Common/font.nftr"
PAL = " .:-=+*#"
f = fontio.Font(SRC)
CW, CH = f.w, f.h
f.glyph = f.glyph7                    # all drawing below works on 0..7 levels; converted back on write
_ink = lambda ch: [y for y, r in enumerate(f.glyph7(f.map[ord(ch)])) if any(r)]
CAP_TOP, BASE = _ink("H")[0], _ink("H")[-1]          # cap height rows (main font: 2..10)
X_TOP = _ink("n")[0]                                  # x-height top (main font 5, Savefont 4)
XH = BASE - X_TOP + 1
STRETCH = XH - 6                                      # extra rows for lowercase drawn for a 6-row x-height
DELTA = f.width(f.map[ord("n")])[2] - f.width(f.map[ord("n")])[1]   # advance minus ink width in this font
BAR_CAP, BAR_X = (CAP_TOP + BASE) // 2, (X_TOP + BASE) // 2
# Savefont is drawn by menu code that adds no letter spacing (measured on the Goods/profile screen: pitch == advance),
# and its Latin glyphs carry faint edge columns instead of side bearings; our drawn letters have solid edges -> +1 px
if "Savefont" in SRC:
    DELTA = max(DELTA, 1)


def art(rows, top):
    g = [[0] * CW for _ in range(CH)]
    for dy, r in enumerate(rows):
        for x, c in enumerate(r):
            g[top + dy][x] = PAL.index(c)
    return g


def gw_of(rows):
    return max(len(r.rstrip()) for r in rows)


def flip(gi):
    g = f.glyph(gi); w = f.width(gi)[1]
    return [row[:w][::-1] + [0] * (CW - w) for row in g]


def shift(g, dx):
    return [([0] * dx + row)[:CW] for row in g]


def put(g, y, x, v=7):
    g[y][x] = v



def mirror_pair(g, w):
    """Glyph g (stem at col 0, arms to the right, width w) -> 'Zh' shape: mirrored copy + original sharing the stem."""
    left = [row[:w][::-1] + [0] * (CW - w) for row in g]
    right = shift(g, w - 1)
    return [[max(a, b) for a, b in zip(lr, rr)] for lr, rr in zip(left, right)]

L = lambda c: f.map[ord(c)]
ART = {}      # char -> (grid, glyph_width)

def A(ch, rows, top=None):
    """Capital (cap height 9 rows, top = CAP_TOP) glyph from ASCII art."""
    ART[ch] = (art(rows, CAP_TOP if top is None else top), gw_of(rows))


def stretch(rows, idx=2):
    """Lowercase art is drawn for a 6-row x-height; fonts with a taller x-height get duplicate row(s)."""
    return rows[:idx + 1] + [rows[idx]] * STRETCH + rows[idx + 1:]


def AL(ch, rows, idx=2):
    """Lowercase glyph from ASCII art: x-height part starts at X_TOP, tails hang below the baseline."""
    ART[ch] = (art(stretch(rows, idx), X_TOP), gw_of(rows))

def draw_big():
    # ---- capitals (cap height 9 rows, top row 2)
    A("Б", ["####*", "#", "#", "#", "###*:", "#  -*", "#   #", "#  -+", "###+."], 2)
    A("Г", ["###*", "#", "#", "#", "#", "#", "#", "#", "#"], 2)
    A("Д", ["  #####", "  #   #", "  #   #", "  #   #", " #    #", " #    #", " #    #", "#     #", "########", "#      #", "#      #"], 2)
    A("Л", ["  #####", "  #   #", "  #   #", " #    #", " #    #", " #    #", "#     #", "#     #", "#     #"], 2)
    A("П", ["#######"] + ["#     #"] * 8, 2)
    A("Ф", ["    #    ", " +##*##+ ", "+-  #  -+", "#   #   #", "#   #   #", "#   #   #", "+-  #  -+", " +##*##+ ", "    #    "], 2)
    A("Ц", ["#    #"] * 8 + ["######*", "      #", "      #"], 2)
    A("Ч", ["#    #", "#    #", "#    #", "+*   #", " :+##*", "     #", "     #", "     #", "     #"], 2)
    A("Ш", ["#   #   #"] * 8 + ["#########"], 2)
    A("Щ", ["#   #   #"] * 8 + ["##########", "         #", "         #"], 2)
    A("Ъ", ["###", "  #", "  #", "  #", "  ###*:", "  #  -*", "  #   #", "  #  -+", "  ###+."], 2)
    A("Ь", ["#", "#", "#", "#", "###*:", "#  -*", "#   #", "#  -+", "###+."], 2)
    A("Ы", ["#     #", "#     #", "#     #", "#     #", "###*: #", "#  -* #", "#   # #", "#  -+ #", "###+. #"], 2)
    # programmatic capitals
    ART["Ж"] = (mirror_pair(f.glyph(L("K")), f.width(L("K"))[1]), 2 * f.width(L("K"))[1] - 1)
    ART["И"] = (flip(L("N")), f.width(L("N"))[1])
    ART["Я"] = ([[min(7, round(7 * (v / 7) ** 0.5)) for v in row] for row in flip(L("R"))], f.width(L("R"))[1])
    g = flip(L("C")); [put(g, BAR_CAP, x) for x in (3, 4, 5)]; ART["Э"] = (g, f.width(L("C"))[1])
    o = f.glyph(L("O")); ow = f.width(L("O"))[1]
    g = shift(o, 3)
    for y in range(CAP_TOP, BASE + 1): put(g, y, 0)
    for x in (1, 2): put(g, BAR_CAP, x)
    ART["Ю"] = (g, ow + 3)
    g = [r[:] for r in ART["И"][0]]
    breve = [[0] * CW for _ in range(2)]
    for x, v in ((0, 5), (6, 5)): breve[0][x] = v
    for x, v in ((1, 4), (2, 6), (3, 7), (4, 6), (5, 4)): breve[1][x] = v
    g[CAP_TOP - 2], g[CAP_TOP - 1] = breve[0], breve[1]; ART["Й"] = (g, ART["И"][1])

    # ---- lowercase (drawn for a 6-row x-height; AL() adapts to the font's x-height)
    ASC = X_TOP - CAP_TOP                                  # ascender rows above the x-height
    BOWL = ["#=##=", "==  ==", "#    #", "#    #", "==  ==", " =##="]
    ART["б"] = (art(["###*:"] + ["#"] * (ASC - 1) + stretch(BOWL), CAP_TOP), 6)
    AL("в", ["###*:", "#  -*", "###*:", "#  -*", "#  -+", "###+."])
    AL("г", ["###*", "#", "#", "#", "#", "#"])
    AL("д", ["  ####", "  #  #", "  #  #", " #   #", "#    #", "#######", "#     #", "#     #"])
    AL("з", ["+##*.", "   -*", " :##:", "   -*", "-  .*", "+##*."])
    AL("и", ["#   #", "#  =#", "# =.#", "#=. #", "#   #", "#   #"])
    ART["й"] = (art(["=   =", " *#* "] + stretch(["#   #", "#  =#", "# =.#", "#=. #", "#   #", "#   #"]), X_TOP - 2), 5)
    kg = f.glyph(L("k"))
    for y in range(CAP_TOP, X_TOP): kg[y] = [0] * CW
    ART["к"] = (kg, f.width(L("k"))[1])
    ART["ж"] = (mirror_pair(kg, f.width(L("k"))[1]), 2 * f.width(L("k"))[1] - 1)
    AL("л", ["  ####", "  #  #", " #   #", " #   #", "#    #", "#    #"])
    AL("м", ["#*   *#", "# * * #", "#  *  #", "#     #", "#     #", "#     #"])
    AL("н", ["#   #", "#   #", "#####", "#   #", "#   #", "#   #"])
    AL("п", ["#####"] + ["#   #"] * 5)
    AL("т", ["#####", "  #", "  #", "  #", "  #", "  #"])
    OVAL = [" =#*#= ", "=  #  =", "#  #  #", "#  #  #", "=  #  =", " =#*#= "]
    ART["ф"] = (art(["   #"] * ASC + stretch(OVAL) + ["   #"] * 2, CAP_TOP), 7)
    AL("ц", ["#   #"] * 5 + ["######", "     #", "     #"])
    AL("ч", ["#   #", "#   #", "*=  #", " +###", "    #", "    #"])
    AL("ш", ["#  #  #"] * 5 + ["#######"])
    AL("щ", ["#  #  #"] * 5 + ["########", "       #", "       #"])
    AL("ъ", ["###", "  #", "  ###*.", "  #  -*", "  #  -+", "  ###+."])
    AL("ь", ["#", "###*:", "#  -*", "#   #", "#  -+", "###+."])
    AL("ы", ["#     #", "###*: #", "#  -* #", "#   # #", "#  -+ #", "###+. #"])
    g = flip(L("c")); [put(g, BAR_X, x) for x in (2, 3, 4)]; ART["э"] = (g, f.width(L("c"))[1])
    o = f.glyph(L("o")); ow = f.width(L("o"))[1]
    g = shift(o, 3)
    for y in range(X_TOP, BASE + 1): put(g, y, 0)
    for x in (1, 2): put(g, BAR_X, x)
    ART["ю"] = (g, ow + 3)
    AL("я", [" ####", "#   #", " ####", "  *:#", " *: #", "*:  #"])


SMALL = CH <= 9           # profile_font: 8x9 cells, caps 5 rows, x-height 4 rows
SPAL = {" ": 0, ".": 2, "=": 5, "#": 7}     # 2-bit font: level 1 -> 2, 2 -> 5, 3 -> 7 on the 0..7 scale


def sart(rows, top):
    g = [[0] * CW for _ in range(CH)]
    for dy, r in enumerate(rows):
        for x, c in enumerate(r):
            g[top + dy][x] = SPAL[c]
    return g


def S_(ch, rows, top):
    ART[ch] = (sart(rows, top), gw_of(rows))


def draw_small():
    # capitals (rows 2..6), tails on rows 7-8
    S_("Б", ["===", "=  ", "==.", "= =", "==."], 2)
    S_("Г", ["==", "= ", "= ", "= ", "= "], 2)
    S_("Д", [" ===", " = =", " = =", " = =", "=====", "=   ="], 2)
    S_("Ж", ["= = =", " === ", "  =  ", " === ", "= = ="], 2)
    S_("З", ["==.", "  =", " =.", "  =", "==."], 2)
    S_("Л", [" ===", " = =", "=  =", "=  =", "=  ="], 2)
    S_("П", ["====", "=  =", "=  =", "=  =", "=  ="], 2)
    S_("Ф", [" === ", "= = =", "= = =", " === ", "  =  "], 2)
    S_("Ц", ["=  =", "=  =", "=  =", "=  =", "=====", "    ="], 2)
    S_("Ч", ["=  =", "=  =", ".===", "   =", "   ="], 2)
    S_("Ш", ["= = =", "= = =", "= = =", "= = =", "====="], 2)
    S_("Щ", ["= = =", "= = =", "= = =", "= = =", "======", "     ="], 2)
    S_("Ъ", ["==", " =", " ==.", " = =", " ==."], 2)
    S_("Ь", ["=  ", "=  ", "==.", "= =", "==."], 2)
    S_("Ы", ["=   =", "=   =", "==. =", "= = =", "==. ="], 2)
    S_("Э", [".==.", "   =", " ===", "   =", ".==."], 2)
    S_("Ю", ["= .==.", "= =  =", "===  =", "= =  =", "= .==."], 2)
    ART["И"] = (flip(L("N")), f.width(L("N"))[1])
    ART["Я"] = (flip(L("R")), f.width(L("R"))[1])
    g = [r[:] for r in ART["И"][0]]; g[1] = sart([".==."], 1)[1]
    ART["Й"] = (g, ART["И"][1])
    # lowercase (rows 3..6), ascenders from row 1, tails rows 7-8
    S_("б", ["==.", "=  ", "==.", "= =", "= =", "==."], 1)
    S_("в", ["==.", "==.", "= =", "==."], 3)
    S_("г", ["==", "= ", "= ", "= "], 3)
    S_("д", [" ===", " = =", "=  =", "====", "=  ="], 3)
    S_("ж", ["= = =", " === ", " === ", "= = ="], 3)
    S_("з", ["==.", " =.", "  =", "==."], 3)
    S_("и", ["= =", "=.=", "==.", "= ="], 3)
    g = sart(["= =", "=.=", "==.", "= ="], 3); g[2] = sart([".=."], 2)[2]
    ART["й"] = (g, 3)
    S_("к", ["= =", "==.", "==.", "= ="], 3)
    S_("л", ["  ==", " = =", "=  =", "=  ="], 3)
    S_("м", ["=   =", "== ==", "= = =", "=   ="], 3)
    S_("н", ["= =", "===", "= =", "= ="], 3)
    S_("п", ["===", "= =", "= =", "= ="], 3)
    S_("т", ["===", " = ", " = ", " = "], 3)
    S_("ф", ["  =  ", "  =  ", " === ", "= = =", "= = =", " === ", "  =  ", "  =  "], 1)
    S_("ц", ["= =", "= =", "= =", "====", "   ="], 3)
    S_("ч", ["= =", "= =", ".==", "  ="], 3)
    S_("ш", ["= = =", "= = =", "= = =", "====="], 3)
    S_("щ", ["= = =", "= = =", "= = =", "======", "     ="], 3)
    S_("ъ", ["==  ", " ==.", " = =", " ==."], 3)
    S_("ь", ["=  ", "==.", "= =", "==."], 3)
    S_("ы", ["=   =", "==. =", "= = =", "==. ="], 3)
    S_("э", ["==.", "  =", " ==", "==."], 3)
    S_("ю", ["= .==.", "===  =", "= =  =", "= .==."], 3)
    S_("я", [".==", "= =", ".==", "= ="], 3)


if SMALL:
    draw_small()
else:
    draw_big()

# Cyrillic р: same bitmap as Latin p, but drawn from the pen (left bearing 0) so it sits as close as the other letters
ART["р"] = (f.glyph(L("p")), f.width(L("p"))[1])
ADV_FIXED = {"р": f.width(L("p"))[1]}

# Cyrillic glyphs that are derived from a Latin one (their advance follows the Latin source)
SRC_OF = {"к": "k", "ж": "k", "и": "n", "й": "n", "э": "c", "ю": "o", "И": "N", "Й": "N", "Я": "R", "Э": "C", "Ю": "O", "Ж": "K"}
ALIAS = dict(zip("АВЕКМНОРСТХУЗЁ", "ABEKMHOPCTXY3Ë")) | dict(zip("аеосхуё", "aeocxyë"))   # р is separate: p has a 1 px left bearing
ALIAS["Н"] = "H"

# ---- choose free glyph slots: Latin-1 letters English text never uses
used = set()
for fn in glob.glob("decoded/Chapter/Pack/*/ue/*.s"):
    for _, b in S.parse(S.read_s(fn))[1]:
        used.update(re.sub(r"<[^>]*>", "", b))
for fn in glob.glob("extracted/data/**/ue/*.txt", recursive=True):
    try:
        used.update(open(fn, "rb").read().decode("utf-16"))
    except UnicodeError:
        pass
cand = [c for c in "ÀÁÂÃÄÅÆÇÊÌÍÎÐÑÒÓÔÕÖØÙÚÛÜÝÞßâãäåæçêìíîðñòóôõöøùúûüýþÿ" if c not in used and ord(c) in f.map]
need = [c for c in ART]
assert len(cand) >= len(need), (len(cand), len(need))
slots = {ch: f.map[ord(c)] for ch, c in zip(need, cand)}

d = f.d
wbase = f.o["cwdh"]["off"]
for ch, (grid, gwid) in ART.items():
    gi = slots[ch]
    f.set_glyph7(gi, grid)
    if ch in ADV_FIXED:
        adv = ADV_FIXED[ch]
    elif ch in SRC_OF:                      # built from a Latin glyph: keep that glyph's "advance minus ink width"
        l_, g_, a_ = f.width(f.map[ord(SRC_OF[ch])])
        adv = gwid + (a_ - g_)
    else:
        adv = gwid + DELTA
    struct.pack_into("<bBB", d, wbase + 3 * gi, 0, gwid, adv)
for lat in ("TY" if os.path.basename(SRC).lower() == "font.nftr" else ""):   # dialogue font only: Cyrillic Т / У share these glyphs and need one more pixel of advance there; menu fonts (no engine spacing) look gappy with it
    gi = f.map[ord(lat)]; l, gw_, ad = f.width(gi)
    struct.pack_into("<bBB", d, wbase + 3 * gi, l, gw_, ad + 1)

pairs = {}
for ch in ART: pairs[ord(ch)] = slots[ch]
for ch, lat in ALIAS.items(): pairs[ord(ch)] = f.map[ord(lat)]

# extend the last CMAP section (explicit code->glyph list, type 2)
sec = [b for b in range(len(d)) if d[b:b + 4] == b"PAMC"][-1]
lo, hi, typ, nxt = struct.unpack_from("<HHHxxI", d, sec + 8)
assert typ == 2 and nxt == 0, (typ, nxt)
n = struct.unpack_from("<H", d, sec + 20)[0]
old = {struct.unpack_from("<HH", d, sec + 22 + 4 * i)[0]: struct.unpack_from("<HH", d, sec + 22 + 4 * i)[1] for i in range(n)}
old.update(pairs)
body = struct.pack("<H", len(old)) + b"".join(struct.pack("<HH", c, g) for c, g in sorted(old.items()))
size = (20 + len(body) + 3) & ~3
new = bytearray(d[:sec + 20]) + body.ljust(size - 20, b"\0")
struct.pack_into("<I", new, sec + 4, size)
struct.pack_into("<I", new, 8, len(new))
os.makedirs(os.path.dirname(OUT), exist_ok=True)
open(OUT, "wb").write(new)
print(f"{len(ART)} glyphs drawn, {len(pairs)} code points added, {len(old)} in extended map; {len(d)} -> {len(new)} bytes -> {OUT}")
print("slots used:", "".join(cand[:len(need)]))
