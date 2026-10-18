"""Edit text sprites in a .pobj (NitroSystem NCGR/NCER) in place: same file size, tiles of a cell are exclusive.
  p = Pobj("decoded/2D/KatharineSave.pobj"); cv = p.canvas(24); cv.text("Да", font, bold=1); p.set_canvas(24, cv); p.save_z("patched_raw/2D/KatharineSave.pobj.z")
Cell canvas = bounding box of the cell's OAMs, pixels are palette indices (None outside OAMs). Text is drawn antialiased by picking the
palette entry of the cell's bank nearest to the blend between background and text colour."""
import os, struct, sys
sys.path.insert(0, os.path.dirname(__file__))
import ds_gfx, fontio, lz10
from pobj_view import cells as _cells, SIZES as P_SIZES
from PIL import Image


class Canvas:
    def __init__(self, oams, w, h, x0, y0):
        self.oams, self.w, self.h, self.x0, self.y0 = oams, w, h, x0, y0
        self.px = [[None] * w for _ in range(h)]

    def mask(self): return [[v is not None for v in r] for r in self.px]

    def clear(self, idx=0):
        for y in range(self.h):
            for x in range(self.w):
                if self.px[y][x] is not None: self.px[y][x] = idx


class Pobj:
    def __init__(self, path):
        self.path = path; self.d = bytearray(open(path, "rb").read()); self.info = ds_gfx.parse(bytes(self.d))
        self.cells, self.shift = _cells(bytes(self.d), self.info); self.pal = self.info["pal"]
        self.tiles = ds_gfx.tile_pixels(bytes(self.d), self.info)
        self._scan_oams()

    def _scan_oams(self):
        pos = [p for m, p, s in self.info["sections"] if m == "RECN"][0]; blk = pos + 16
        cnt, attr, off, _ = struct.unpack_from("<HHII", self.d, blk + 8)
        base = blk + 8 + off; step = 16 if attr & 1 else 8; self.oam_off = []
        for i in range(cnt):
            n, cattr, ooff = struct.unpack_from("<HHI", self.d, base + i * step)
            ob = base + cnt * step + ooff; self.oam_off.append([ob + 6 * k for k in range(n)])
        self.units = len(self.tiles) // 4; self.free = set(range(self.units))
        for c in self.cells:
            for o in c: self.free -= self._units(o)

    @staticmethod
    def _units(o):
        n = (o["w"] // 8) * (o["h"] // 8); return set(range(o["tile"], o["tile"] + (n + 3) // 4))

    def alloc(self, tiles):
        """Allocate `tiles` tiles (rounded up to 4-tile OAM units) from unused units; returns the OAM tile number."""
        units = (tiles + 3) // 4
        for u in sorted(self.free):
            if all(u + i in self.free for i in range(units)):
                for i in range(units): self.free.discard(u + i)
                for t in range(u * 4, (u + units) * 4): self.tiles[t] = [0] * 64
                return u
        raise RuntimeError("no free tile units left in %s" % self.path)

    def write_oam(self, ci, k, o):
        shape = {(w, h): (sh, sz) for (sh, sz), (w, h) in P_SIZES.items()}[(o["w"], o["h"])]
        off = self.oam_off[ci][k]; a0, a1, a2 = struct.unpack_from("<HHH", self.d, off)
        a0 = (a0 & 0x3F00) | (o["y"] & 0xFF) | (shape[0] << 14)
        a1 = (a1 & 0x3000) | (o["x"] & 0x1FF) | (shape[1] << 14)
        a2 = (a2 & 0x0C00) | (o["tile"] & 0x3FF) | (o["bank"] << 12)
        struct.pack_into("<HHH", self.d, off, a0, a1, a2); self.cells[ci][k] = o

    def relayout(self, ci, W):
        """Widen the cell to W pixels (multiple of 8), existing OAMs are re-sized/re-pointed to fresh tiles; old pixels are stretched
        by repeating the middle column (so frames keep their edges). Returns the new canvas."""
        old = self.canvas(ci); oams = [dict(o) for o in self.cells[ci]]
        if W <= old.w: return old
        for o in self.cells[ci]: self.free |= self._units(o)
        rows = {}
        for k, o in enumerate(oams): rows.setdefault(o["y"], []).append(k)
        for y, ks in rows.items():
            h = oams[ks[0]]["h"]; ks.sort(key=lambda k: oams[k]["x"]); x = min(oams[k]["x"] for k in ks)
            allowed = [32, 16, 8] if h in (8, 16) else None
            if allowed is None: raise ValueError("cell %d row height %d not supported" % (ci, h))
            remaining = W - 0; wl = []
            for _ in ks:
                if remaining <= 0: break
                w = next(a for a in allowed if a <= remaining) if remaining >= 8 else 8
                w = min(32, max(8, w)); wl.append(w); remaining -= w
            if remaining > 0: raise ValueError("cell %d: width %d needs more OAMs" % (ci, W))
            for j, k in enumerate(ks):
                o = oams[k]
                if j < len(wl):
                    o["w"] = wl[j]; o["x"] = x; x += wl[j]
                else:
                    o["w"], o["h"] = 8, h; o["x"] = x   # unused slot: blank 8-wide strip
                o["tile"] = self.alloc((o["w"] // 8) * (o["h"] // 8))
                self.write_oam(ci, k, o)
        new = self.canvas(ci); half = old.w // 2
        for y in range(new.h):
            for x in range(new.w):
                if new.px[y][x] is None: continue
                ox = x if x < half else (x - (new.w - old.w) if x >= new.w - (old.w - half) else half)
                oy = min(max(y, 0), old.h - 1); v = old.px[oy][min(max(ox, 0), old.w - 1)]
                new.px[y][x] = 0 if v is None else v
        self.set_canvas(ci, new)
        return new

    # -- canvases --
    def canvas(self, ci):
        oams = self.cells[ci]
        x0 = min(o["x"] for o in oams); y0 = min(o["y"] for o in oams)
        x1 = max(o["x"] + o["w"] for o in oams); y1 = max(o["y"] + o["h"] for o in oams)
        cv = Canvas(oams, x1 - x0, y1 - y0, x0, y0)
        for o in oams:
            for (X, Y, idx, x, y) in self._pixels(o):
                cv.px[o["y"] - y0 + Y][o["x"] - x0 + X] = self.tiles[idx][y * 8 + x]
        return cv

    def _pixels(self, o):
        t = o["tile"] << self.shift
        for ty in range(o["h"] // 8):
            for tx in range(o["w"] // 8):
                idx = t + ty * (o["w"] // 8) + tx
                for y in range(8):
                    for x in range(8):
                        X = tx * 8 + x; Y = ty * 8 + y
                        if o["hf"]: X = o["w"] - 1 - X
                        if o["vf"]: Y = o["h"] - 1 - Y
                        yield X, Y, idx, x, y

    def set_canvas(self, ci, cv):
        for o in cv.oams:
            for (X, Y, idx, x, y) in self._pixels(o):
                v = cv.px[o["y"] - cv.y0 + Y][o["x"] - cv.x0 + X]
                self.tiles[idx][y * 8 + x] = v

    def save_z(self, out):
        d = bytearray(self.d); off = self.info["tile_off"]
        for i, t in enumerate(self.tiles):
            d[off + 32 * i: off + 32 * i + 32] = ds_gfx._pack_tile(t, 4)
        os.makedirs(os.path.dirname(out), exist_ok=True)
        open(out, "wb").write(lz10.compress(bytes(d)))

    # -- preview --
    def render(self, ci, scale=4, bg=(60, 60, 90)):
        cv = self.canvas(ci); bank = self.cells[ci][0]["bank"]
        im = Image.new("RGB", (cv.w, cv.h), bg); px = im.load()
        for y in range(cv.h):
            for x in range(cv.w):
                v = cv.px[y][x]
                if v: px[x, y] = self.pal[bank * 16 + v]
        return im.resize((cv.w * scale, cv.h * scale), Image.NEAREST)


def glyph_cov(font, ch):
    gi = font.map.get(ord(ch))
    if gi is None: gi = font.map.get(ord("?"))
    left, gw, adv = font.width(gi)
    g = font.glyph7(gi)
    return g, left, gw, adv


def text_coverage(text, font, bold=1, space=1, keep_adv=True):
    """-> (rows of coverage 0..1, width). bold=n widens strokes by n px to the right."""
    H = font.h; cols = []; x = 0; width = 0; cov = [[0.0] * 400 for _ in range(H)]
    for ch in text:
        g, left, gw, adv = glyph_cov(font, ch)
        for y in range(H):
            for gx in range(font.w):
                v = g[y][gx] / 7.0
                if v:
                    for b in range(bold + 1):
                        X = x + left + gx + b
                        if X < 400: cov[y][X] = max(cov[y][X], v)
        x += adv + space + bold
    return [r[:x] for r in cov], x


def squeeze(cov, w, target, gain=1.35):
    """Horizontal area-sampling of a coverage bitmap from width w to `target` (antialiased condensed text)."""
    if target >= w: return cov, w
    k = w / target; out = []
    for row in cov:
        r = []
        for x in range(target):
            a, b = x * k, (x + 1) * k; tot = 0.0; i = int(a)
            while i < b and i < w:
                lo, hi = max(a, i), min(b, i + 1); tot += row[i] * max(0.0, hi - lo); i += 1
            r.append(min(1.0, tot / k * gain))
        out.append(r)
    return out, target


def nearest(pal16, target):
    best, bd = 1, 10**9
    for i in range(1, 16):
        c = pal16[i]; dd = sum((a - b) ** 2 for a, b in zip(c, target))
        if dd < bd: best, bd = i, dd
    return best


def find_holes(mask, w):
    """Column intervals (a, b) strictly inside the cell that no OAM covers (text must not be drawn there)."""
    cov = [any(r[x] for r in mask) for x in range(w)]
    xs = [x for x in range(w) if cov[x]]
    if not xs: return []
    holes = []; x = min(xs)
    while x <= max(xs):
        if not cov[x]:
            a = x
            while not cov[x]: x += 1
            holes.append((a, x - 1))
        else: x += 1
    return holes


def column_map(cov, w, x0, holes, minx, maxx):
    """Canvas x for every text column, or None if it does not fit. Columns after a hole jump over it; the break is put in a blank text
    column (preferably a word gap) near the hole, so no letter is cut in two. The left part may be shifted left to make room."""
    blank = [not any(row[c] > 0 for row in cov) for c in range(w)]
    pos = [x0 + c for c in range(w)]
    for a, b in holes:
        k = a - x0
        if k <= 0 or k >= w - 1:
            if k >= w - 1: continue
            return None
        best = None
        for c in range(max(0, k - 12), min(w - 1, k + 12) + 1):
            if not blank[c]: continue
            run = 1
            while c + run < w and blank[c + run]: run += 1
            left_shift = max(0, pos[c] - (a - 1))
            if pos[0] - left_shift < minx: continue
            end = (b + 1) + (w - 1 - (c + 1)) + 0
            if pos[w - 1] - 0 >= 0 and end > maxx: continue
            score = (0 if run >= 3 else 1, left_shift + abs(c - k))
            if best is None or score < best[0]: best = (score, c, left_shift)
        if best is None: return None
        _, c, ls = best
        for i in range(c + 1): pos[i] -= ls
        for i in range(c + 1, w): pos[i] = (b + 1) + (i - c - 1)
    return pos


def draw_text(p, ci, cv, text, font, bold=1, x=None, y=None, fg=None, bg=None, align="center", yoff=0, space=1, maxw=None, thresh=None):
    """Draw text into canvas cv of cell ci. fg/bg: palette indices (default: brightest / darkest non-zero index used in the cell)."""
    bank = p.cells[ci][0]["bank"]; pal = [p.pal[bank * 16 + i] for i in range(16)]
    used = sorted({v for r in cv.px for v in r if v})
    lum = lambda i: sum(pal[i])
    fgi = fg if fg is not None else max(used, key=lum); bgi = bg if bg is not None else min(used, key=lum)
    cov0, w0 = text_coverage(text, font, bold, space)
    mask = cv.mask(); holes = find_holes(mask, cv.w)
    xs_all = [xx for xx in range(cv.w) if any(r[xx] for r in mask)]; minx, maxx = min(xs_all), max(xs_all)
    hole_total = sum(b - a + 1 for a, b in holes)
    limit = min(maxw or cv.w, maxx - minx + 1) - hole_total
    cov, w = (squeeze(cov0, w0, limit) if w0 > limit else (cov0, w0)); cols = None
    while True:
        if x is None: x0 = {"left": minx, "center": minx + ((maxx - minx + 1 - hole_total) - w) // 2, "right": maxx - w + 1}[align]
        else: x0 = x
        cols = column_map(cov, w, x0, holes, minx, maxx)
        if cols is not None or w <= 8: break
        cov, w = squeeze(cov0, w0, w - 1)
    H = len(cov)
    ys = [yy for yy in range(cv.h) if any(mask[yy])]
    top, bot = min(ys), max(ys)
    ink = [yy for yy in range(H) if any(cov[yy])]; it, ib = (min(ink), max(ink)) if ink else (0, 0)
    if y is None: y = top + (bot - top + 1 - (ib - it + 1)) // 2 - it + yoff
    cv.clear(0)
    for yy in range(H):
        for xx in range(w):
            c = cov[yy][xx]
            if c <= 0 or (thresh and c < thresh): continue
            X, Y = cols[xx], y + yy
            if 0 <= X < cv.w and 0 <= Y < cv.h and mask[Y][X]:
                tgt = tuple(int(pal[bgi][k] + (pal[fgi][k] - pal[bgi][k]) * min(1.0, c * 1.15)) for k in range(3))
                cv.px[Y][X] = nearest(pal, tgt) if (c < 0.99 and not thresh) else fgi
    return w


def interior(cv):
    """Interior of a framed cell: the bounding box of the most common non-zero colour (the cell's fill). -> (x0,y0,x1,y1,bg,fg)."""
    import collections
    cnt = collections.Counter(v for r in cv.px for v in r if v)
    bgv = cnt.most_common(1)[0][0]
    xs = [x for r in cv.px for x, v in enumerate(r) if v == bgv]; ys = [y for y, r in enumerate(cv.px) if bgv in r]
    return min(xs), min(ys), max(xs), max(ys), bgv


def draw_boxed(p, ci, cv, lines, font, bold=1, space=(5, 1), margin=3, gap=2, gain=1.35, fg=None, maxscale=1.0):
    """Replace the text inside a framed cell: interior is cleared to its fill colour, lines are centred. `space` = (max,min) letter spacing:
    the widest spacing that fits is used, otherwise the line is squeezed."""
    x0, y0, x1, y1, bgv = interior(cv)
    bank = p.cells[ci][0]["bank"]; pal = [p.pal[bank * 16 + i] for i in range(16)]
    used = {v for r in cv.px for v in r if v}
    fgi = fg if fg is not None else max(used, key=lambda i: sum(pal[i]))
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            if cv.px[y][x] is not None: cv.px[y][x] = bgv
    avail = (x1 - x0 + 1) - 2 * margin; covs = []
    for t in lines:
        sp = space[0] if isinstance(space, tuple) else space; lo = space[1] if isinstance(space, tuple) else space
        while True:
            cov, w = text_coverage(t, font, bold, sp)
            if w <= avail or sp <= lo: break
            sp -= 1
        if w > avail: cov, w = squeeze(cov, w, avail, gain)
        ink = [yy for yy in range(len(cov)) if any(cov[yy])]; it, ib = min(ink), max(ink); covs.append((cov[it:ib + 1], w))
    total = sum(len(c) for c, _ in covs) + gap * (len(covs) - 1); y = y0 + ((y1 - y0 + 1) - total) // 2
    for cov, w in covs:
        x = x0 + ((x1 - x0 + 1) - w) // 2
        for yy, row in enumerate(cov):
            for xx in range(w):
                c = row[xx]
                if c <= 0: continue
                tgt = tuple(int(pal[bgv][k] + (pal[fgi][k] - pal[bgv][k]) * min(1.0, c)) for k in range(3))
                if cv.px[y + yy][x + xx] is not None: cv.px[y + yy][x + xx] = nearest(pal, tgt) if c < 0.99 else fgi
        y += len(cov) + gap
