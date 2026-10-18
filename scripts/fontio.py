"""Read/write glyph bitmaps of NFTR fonts (bit-packed, MSB first, row-major)."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import nftr


class Font:
    def __init__(self, path):
        self.d = bytearray(open(path, "rb").read()); self.o = nftr.parse(bytes(self.d)); g = self.o["cglp"]
        self.w, self.h, self.bpp, self.cell, self.off = g["cell_w"], g["cell_h"], g["depth"], g["cell_bytes"], g["data_off"]
        self.map = self.o["map"]; self.n = g["glyphs"]

    def glyph(self, gi):
        base = self.off + gi * self.cell
        bits = int.from_bytes(self.d[base:base + self.cell], "big"); total = self.cell * 8
        m = (1 << self.bpp) - 1
        return [[(bits >> (total - self.bpp * (y * self.w + x + 1))) & m for x in range(self.w)] for y in range(self.h)]

    def set_glyph(self, gi, rows):
        total = self.cell * 8; bits = 0; m = (1 << self.bpp) - 1
        for y in range(self.h):
            for x in range(self.w):
                bits |= (rows[y][x] & m) << (total - self.bpp * (y * self.w + x + 1))
        base = self.off + gi * self.cell
        self.d[base:base + self.cell] = bits.to_bytes(self.cell, "big")

    def glyph7(self, gi):
        """Glyph with levels normalised to 0..7 (any bit depth)."""
        m = (1 << self.bpp) - 1
        return [[round(v * 7 / m) for v in row] for row in Font.glyph(self, gi)]

    def set_glyph7(self, gi, rows):
        m = (1 << self.bpp) - 1
        self.set_glyph(gi, [[min(m, round(v * m / 7)) for v in row] for row in rows])

    def width(self, gi):
        return self.o["widths"][gi]          # (left, glyph_w, advance)


if __name__ == "__main__":
    f = Font(sys.argv[1])
    for ch in sys.argv[2]:
        gi = f.map[ord(ch)]; print(ch, "glyph", gi, "width(left,glyph,adv)", f.width(gi))
        for row in f.glyph(gi): print("".join(" .:-=+*#"[v] for v in row))
