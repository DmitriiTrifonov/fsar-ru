"""stage4_lostbg.py: Russian title strip of the LostList card backgrounds (lostBG_u: hotel name + 'Lost and Found Report').
The tiny captions (date line, guests line, 'presents') are 5-6 px tall decoration and are left alone.
Output: patched_raw/LostList/ue/lostBG_u.pbg.z (kept inside its ROM slot, see AGENTS.md: savestates keep the file table)."""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
import ds_gfx, lz10, fontio, pobj_edit as E
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAIN = fontio.Font(f"{ROOT}/patched_raw/Chapter/Pack/Common/font.nftr")

def cover(text, w_max, h, bold=1):
    cov, w = E.text_coverage(text, MAIN, bold=bold, space=0)
    a = np.array(cov); a = a[:, :w]
    ys = np.where(a.max(axis=1) > 0.05)[0]; a = a[ys.min():ys.max() + 1]
    sh, sw = a.shape; s = h / sh; nw = min(w_max, int(round(sw * s))); nh = h
    out = np.zeros((nh, nw))
    for y in range(nh):
        for x in range(nw):
            y0, y1 = y * sh / nh, (y + 1) * sh / nh; x0, x1 = x * sw / nw, (x + 1) * sw / nw
            out[y, x] = a[int(y0):max(int(y0) + 1, int(np.ceil(y1))), int(x0):max(int(x0) + 1, int(np.ceil(x1)))].mean()
    return out

SUP = "/System/Library/Fonts/Supplemental/"
FONT = {"top": "Tahoma Bold.ttf", "title": "Tahoma Bold.ttf"}

def cover_tt(text, fontfile, h, w_max):
    """Supersampled TrueType coverage whose ink box is h rows high (width follows the font, squeezed only if wider than w_max)."""
    from PIL import Image, ImageDraw, ImageFont
    K = 8
    best = None
    for size in range(h * K, 4, -1):
        f = ImageFont.truetype(SUP + fontfile, size)
        l, t, r, b = f.getbbox(text)
        if b - t <= h * K: best = (f, l, t, r, b); break
    f, l, t, r, b = best
    im = Image.new("L", (r - l + 2, b - t + 2), 0); ImageDraw.Draw(im).text((-l + 1, -t + 1), text, font=f, fill=255)
    a = np.array(im, dtype=float) / 255.0
    ys = np.where(a.max(axis=1) > 0.1)[0]; xs = np.where(a.max(axis=0) > 0.1)[0]; a = a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    sh, sw = a.shape; nh = h; nw = min(w_max, max(1, int(round(sw * h / sh)))); out = np.zeros((nh, nw))
    for y in range(nh):
        for x in range(nw):
            y0, y1 = y * sh / nh, (y + 1) * sh / nh; x0, x1 = x * sw / nw, (x + 1) * sw / nw
            out[y, x] = a[int(y0):max(int(y0) + 1, int(np.ceil(y1))), int(x0):max(int(x0) + 1, int(np.ceil(x1)))].mean()
    return out

def run(src, dst):
    d = lz10.decompress(open(src, "rb").read()); info = ds_gfx.parse(d); rows = ds_gfx.decode_indexed(d, info); pal = info["pal"]
    BGROW = {}; INK = pal[3]; dark = lambda i: sum(pal[i]) < 420 and i != 1
    out = [r[:] for r in rows]
    import collections
    def place(y0, y1, text, h, bold=1, x_lo=6, x_hi=249, wipe=None, kind=None):
        # background per row = the clean left margin of the card (x=4); the whole box is wiped (old brackets included)
        wy0, wy1 = wipe or (y0, y1)
        for y in range(wy0, wy1 + 1):
            BGROW[y] = rows[y][4]
            for x in range(x_lo, x_hi + 1): out[y][x] = BGROW[y]
        c = cover_tt(text, FONT[kind], h, x_hi - x_lo) if kind else cover(text, x_hi - x_lo, h, bold); ch, cw = c.shape; xs = (x_lo + x_hi - cw) // 2 + 1; ys = y0 + (y1 - y0 + 1 - ch) // 2
        for y in range(ch):
            bg = pal[BGROW[ys + y]]
            for x in range(cw):
                v = min(1.0, c[y, x] * 1.15)
                v = 0.0 if v < 0.25 else (0.55 if v < 0.65 else 1.0)
                if v == 0.0: continue
                t = tuple(bg[k] + (INK[k] - bg[k]) * v for k in range(3))
                out[ys + y][xs + x] = min(range(2, 256), key=lambda i: sum((a - b) ** 2 for a, b in zip(pal[i], t)))
    place(17, 27, "ОТЕЛЬ «Цветок, Солнце и Дождь»", 10, bold=1, x_lo=5, x_hi=250, kind="top")
    place(29, 43, "[Список находок]", 15, bold=1, x_lo=3, x_hi=252, wipe=(28, 48), kind="title")
    nd, _, _ = ds_gfx.repack(d, info, out)
    nd = ds_gfx.compact(nd)                      # repack only appends tiles; compact drops the unused old text tiles (file shrinks a lot)
    z = lz10.compress_opt(nd)
    orig = len(open(src, "rb").read())
    assert len(z) <= orig, (len(z), orig)
    z += bytes(orig - len(z))                    # pad with zeros to the original size: every later file keeps its offset (savestates!)
    print("size", len(z))
    open(dst, "wb").write(z); print(dst, len(z))
    return ds_gfx.render_screen(nd, ds_gfx.parse(nd))

if __name__ == "__main__":
    im = run(f"{ROOT}/extracted/data/LostList/ue/lostBG_u.pbg.z", f"{ROOT}/patched_raw/LostList/ue/lostBG_u.pbg.z")
    im.save(f"{ROOT}/dumps/gfx/lostbg_u.png")
