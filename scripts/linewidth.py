"""Pixel width of a text line as the game draws it: sum(advance + 1) per char, last char counted by its ink width.
Measured in-game: 28 x 'н' (adv 6, ink 5) -> ink spans 193.8 px = 28*7-2."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import fontio

_FONT = {}


def font(path="patched_raw/Chapter/Pack/Common/font.nftr"):
    if path not in _FONT:
        _FONT[path] = fontio.Font(path)
    return _FONT[path]


def width(line, f=None):
    f = f or font()
    if not line:
        return 0
    total = 0
    for i, ch in enumerate(line):
        gi = f.map.get(ord(ch))
        if gi is None:
            gi = f.map.get(ord("?"))
        left, gw, adv = f.width(gi)
        total += (adv + 1) if i < len(line) - 1 else gw
    return total

if __name__ == "__main__":
    for t in sys.argv[1:]:
        print(width(t), t)
