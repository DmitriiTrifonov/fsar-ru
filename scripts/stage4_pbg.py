"""Этап 4: русские надписи в фоновых .pbg (экраны сохранений, диск Катарины).
Берёт decoded/2D/ue/*.pbg, стирает английскую надпись, рисует кириллицу (TTF macOS, перспектива, обводка,
палитра картинки), делает ds_gfx.repack и пишет LZ10 в patched_raw/2D/ue/<имя>.pbg.z.
Превью до/после: dumps/gfx/pbg_preview/<имя>.png (x3). Идемпотентен.
usage: tools/venv/bin/python -I scripts/stage4_pbg.py [имя ...]"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ds_gfx, lz10
from PIL import Image, ImageDraw, ImageFont, ImageChops, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SUP = "/System/Library/Fonts/Supplemental/"
S = 4  # суперсэмплинг


def font(name, size):
    return ImageFont.truetype(SUP + name, size)


def solve_persp(dst, src):
    """коэффициенты PERSPECTIVE (dst -> src), 4 точки"""
    A, B = [], []
    for (x, y), (u, v) in zip(dst, src):
        A.append([x, y, 1, 0, 0, 0, -u * x, -u * y]); B.append(u)
        A.append([0, 0, 0, x, y, 1, -v * x, -v * y]); B.append(v)
    n = 8
    for i in range(n):
        p = max(range(i, n), key=lambda r: abs(A[r][i]))
        A[i], A[p] = A[p], A[i]; B[i], B[p] = B[p], B[i]
        for r in range(n):
            if r != i:
                f = A[r][i] / A[i][i]
                A[r] = [a - f * b for a, b in zip(A[r], A[i])]; B[r] -= f * B[i]
    return [B[i] / A[i][i] for i in range(n)]


def draw_tracked(draw, xy, text, fnt, fill, track):
    x, y = xy
    for ch in text:
        draw.text((x, y), ch, font=fnt, fill=fill)
        x += fnt.getlength(ch) + track


def word_layer(text, fnt, quad, size, italic=0.0, track=0):
    """Маска текста, вписанная по ink-ширине и высоте заглавных в четырёхугольник quad (TL,TR,BR,BL, пиксели картинки).
    Результат: L-слой size*S."""
    W = int(fnt.getlength(text) + track * len(text)) + 200
    H = int(fnt.size * 2)
    src = Image.new("L", (W, H), 0)
    draw_tracked(ImageDraw.Draw(src), (50, int(fnt.size * 0.3)), text, fnt, 255, track)
    if italic:
        src = src.transform(src.size, Image.AFFINE, (1, italic, -italic * H * 0.6, 0, 1, 0), Image.BICUBIC)
    cap = ImageFont.truetype(fnt.path, fnt.size).getmask("П").getbbox()
    bb = src.getbbox()
    x0, x1 = bb[0], bb[2]
    # высота заглавных: верх 'П' и базовая линия
    capimg = Image.new("L", (W, H), 0); ImageDraw.Draw(capimg).text((50, int(fnt.size * 0.3)), "ПЕ", font=fnt, fill=255)
    cb = capimg.getbbox(); top, base = cb[1], cb[3]
    srcq = [(x0, top), (x1, top), (x1, base), (x0, base)]
    dstq = [(x * S, y * S) for x, y in quad]
    co = solve_persp(dstq, srcq)
    return src.transform((size[0] * S, size[1] * S), Image.PERSPECTIVE, co, Image.BICUBIC)


def shift(img, dx, dy):
    return ImageChops.offset(img, int(round(dx * S)), int(round(dy * S)))


def composite(size, layers):
    """layers: [(mask(L, size*S), (r,g,b))] снизу вверх -> RGB size (с усреднением)"""
    big = Image.new("RGB", (size[0] * S, size[1] * S), (0, 0, 0))
    for m, col in layers:
        big.paste(Image.new("RGB", big.size, col), (0, 0), m)
    return big.resize(size, Image.BOX)


def grow(m, px):
    k = int(px * S) * 2 + 1
    return m.filter(ImageFilter.MaxFilter(k if k % 2 else k + 1))


def nearest(pal_sub, rgb):
    r, g, b = rgb
    best, bd = None, 1e9
    for i, (pr, pg, pb) in pal_sub:
        d = (pr - r) ** 2 * 2 + (pg - g) ** 2 * 4 + (pb - b) ** 2 * 3
        if d < bd:
            best, bd = i, d
    return best


def paint(rows, info, rgb, region, keep_mask=None, orig=None):
    """Записывает RGB-картинку в индексы палитры внутри region=(x0,y0,x1,y1), подпалитра = цвета этой области + чёрный."""
    x0, y0, x1, y1 = region
    pal = info["pal"]
    used = {(orig or rows)[y][x] for y in range(y0, y1) for x in range(x0, x1) if not (keep_mask and keep_mask(x, y))} | {rows[0][255]}
    sub = [(i, pal[i]) for i in sorted(used)]
    cache = {}
    px = rgb.load()
    for y in range(y0, y1):
        for x in range(x0, x1):
            if keep_mask and keep_mask(x, y):
                continue
            c = px[x, y]
            if c not in cache:
                cache[c] = nearest(sub, c)
            rows[y][x] = cache[c]


def make_save(name, items, region, keep, fill, edge, hi=None, extra=None):
    d = open(f"{ROOT}/decoded/2D/ue/{name}.pbg", "rb").read()
    info = ds_gfx.parse(d)
    rows = ds_gfx.decode_indexed(d, info)
    before = ds_gfx.render_screen(d, info)
    x0, y0, x1, y1 = region
    bg = rows[0][255]
    pal_rows = [r[:] for r in rows]
    for y in range(y0, y1):
        for x in range(x0, x1):
            if not keep(x, y):
                rows[y][x] = bg
    size = (256, 256)
    layers = []
    masks = []
    for text, fname, fsize, quad, ital, *tr in items:
        masks.append(word_layer(text, font(fname, fsize), quad, size, ital, tr[0] if tr else 0))
    m_all = masks[0]
    for m in masks[1:]:
        m_all = ImageChops.lighter(m_all, m)
    # слои: тень/край справа-снизу, подсветка слева, заливка
    layers.append((shift(m_all, 1.0, 0.4), edge))
    if hi:
        layers.append((shift(m_all, -1.0, 0), hi))
    layers.append((m_all, fill))
    rgb = composite(size, layers)
    paint(rows, info, rgb, region, lambda x, y: keep(x, y), pal_rows)
    out, changed, newt = ds_gfx.repack(d, info, rows)
    return d, out, before, rows, changed, newt


def save_outputs(name, d, out, before, rel):
    info2 = ds_gfx.parse(out)
    back = ds_gfx.decode_indexed(out, info2)
    img = ds_gfx.render_screen(out, info2)
    # приводим к строкам: декодирование результата должно совпасть с нарисованным
    z = lz10.compress(out)
    assert lz10.decompress(z) == out
    dst = f"{ROOT}/patched_raw/{rel}/{name}.pbg.z"
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    open(dst, "wb").write(z)
    pv = f"{ROOT}/dumps/gfx/pbg_preview"
    os.makedirs(pv, exist_ok=True)
    w = Image.new("RGB", (256 * 3, 192 * 3 * 2 + 4), (60, 0, 60))
    w.paste(before.crop((0, 0, 256, 192)).resize((768, 576), Image.NEAREST), (0, 0))
    w.paste(img.crop((0, 0, 256, 192)).resize((768, 576), Image.NEAREST), (0, 580))
    w.save(f"{pv}/{name}.png")
    return back


def keep_star(x, y):
    return x < 40 and y < 38


def job_edo01():
    top, bot = 0, 0
    items = [
        ("ЭДО МАКАЛИСТЕР", "Arial Narrow Bold Italic.ttf", 100, [(29, 45), (131, 12), (131, 22), (29, 54)], 0.0),
        ("Привет!!", "Arial Black.ttf", 100, [(25, 59), (82, 56), (82, 75), (25, 77)], 0.0, 3),
        ("СОХРАНЕНИЕ", "Arial Narrow Bold.ttf", 100, [(91, 47), (245, 14), (245, 70), (91, 74)], 0.0, 8),
    ]
    return make_save("save_edo01", items, (22, 3, 252, 80), keep_star, (255, 0, 120), (170, 0, 70), hi=(255, 255, 255))


def job_edo02():
    items = [
        ("ПРИВЕТ?", "Arial Narrow Bold Italic.ttf", 100, [(20, 42), (66, 24), (66, 34), (20, 52)], 0.0),
        ("ЭДО МАКАЛИСТЕР", "Arial Narrow Bold Italic.ttf", 100, [(18, 56), (140, 27), (140, 70), (18, 69)], 0.0, 6),
    ]
    return make_save("save_edo02", items, (14, 3, 200, 80), keep_star, (255, 0, 120), (170, 0, 70), hi=(255, 255, 255))


def job_sue01():
    items = [
        ("СЬЮ СДИНГ", "Arial Black.ttf", 100, [(27, 44), (137, 9), (137, 19), (27, 55)], 0.0),
        ("Привет!!", "Arial Black.ttf", 100, [(25, 59), (82, 56), (82, 75), (25, 77)], 0.0, 3),
        ("СОХРАНЕНИЕ", "Arial Narrow Bold.ttf", 100, [(91, 47), (245, 14), (245, 70), (91, 74)], 0.0, 8),
    ]
    return make_save("save_sue01", items, (22, 3, 252, 80), keep_star, (255, 255, 0), (230, 90, 0))


def job_sue02():
    items = [
        ("ПРИВЕТ?", "Arial Narrow Bold Italic.ttf", 100, [(18, 44), (66, 24), (66, 35), (18, 54)], 0.0),
        ("СЬЮ СДИНГ", "Arial Narrow Bold Italic.ttf", 100, [(17, 58), (128, 30), (128, 71), (17, 71)], 0.0, 6),
    ]
    return make_save("save_sue02", items, (14, 3, 200, 80), keep_star, (255, 255, 0), (230, 90, 0))



# ---------- диск Катарины (4 bpp: в каждой ячейке 8x8 только цвета её банка из 16) ----------
def luma(c):
    return 0.3 * c[0] + 0.59 * c[1] + 0.11 * c[2]


def inpaint(img, mask, rounds=6):
    """закрашивает пиксели mask медианой соседних немаскированных (по 3 пикселя вокруг)"""
    px = img.load(); W, H = img.size
    mk = set(mask)
    for _ in range(rounds):
        if not mk:
            break
        done = {}
        for (x, y) in mk:
            vals = [px[xx, yy] for yy in range(y - 3, y + 4) for xx in range(x - 3, x + 4)
                    if 0 <= xx < W and 0 <= yy < H and (xx, yy) not in mk]
            if len(vals) >= 6:
                done[(x, y)] = tuple(sorted(v[k] for v in vals)[len(vals) // 2] for k in range(3))
        for k, v in done.items():
            px[k] = v; mk.discard(k)


def dilate(pts, r, box):
    x0, y0, x1, y1 = box
    out = set()
    for (x, y) in pts:
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                if x0 <= x + dx < x1 and y0 <= y + dy < y1:
                    out.add((x + dx, y + dy))
    return out


def paint_banks(rows, info, rgb, cells_px):
    """cells_px: пиксели для записи; цвет берётся из 16 цветов банка ячейки"""
    pal = info["pal"]; cache = {}
    for (x, y) in cells_px:
        bank = rows[y // 8 * 8][x // 8 * 8] >> 4
        c = rgb.getpixel((x, y)); key = (bank, c)
        if key not in cache:
            sub = [(bank * 16 + k, pal[bank * 16 + k]) for k in range(16)]
            cache[key] = nearest(sub, c)
        rows[y][x] = cache[key]


def arc_text(text, fnt, center, radius, step_deg, color, size, rot_extra=0):
    import math
    big = Image.new("L", (size[0] * S, size[1] * S), 0)
    n = len(text)
    for i, ch in enumerate(text):
        th = (i - (n - 1) / 2) * step_deg
        cb = Image.new("L", (fnt.size * 2, fnt.size * 2), 0)
        ImageDraw.Draw(cb).text((fnt.size, fnt.size), ch, font=fnt, fill=255, anchor="mm")
        cb = cb.rotate(-th + rot_extra, Image.BICUBIC)
        cx = center[0] + radius * math.sin(math.radians(th)); cy = center[1] - radius * math.cos(math.radians(th))
        big.paste(255, (int(cx * S - cb.width / 2), int(cy * S - cb.height / 2)), cb)
    return big


def make_katharune():
    name = "katharune_01"
    d = open(f"{ROOT}/decoded/2D/ue/{name}.pbg", "rb").read()
    info = ds_gfx.parse(d)
    rows = ds_gfx.decode_indexed(d, info)
    before = ds_gfx.render_screen(d, info)
    rgb = before.copy(); px = rgb.load(); size = (256, 256)
    touched = set()

    def process(box, is_text, label, color, build_mask, fill=None, gain=1.0):
        x0, y0, x1, y1 = box
        txt = {(x, y) for y in range(y0, y1) for x in range(x0, x1) if is_text(px[x, y])}
        halo = dilate(txt, 1, box)
        if fill:
            for k in halo:
                px[k] = fill
        else:
            inpaint(rgb, halo)
        big = build_mask()
        m = big.resize(size, Image.BOX)
        mp = m.load(); pp = rgb.load()
        for y in range(y0, y1):
            for x in range(x0, x1):
                a = min(1.0, mp[x, y] / 255 * gain)
                if a > 0.02:
                    bgc = pp[x, y]
                    pp[x, y] = tuple(int(bgc[k] * (1 - a) + color[k] * a) for k in range(3))
        touched.update((x, y) for y in range(y0, y1) for x in range(x0, x1))

    # SELECT -> ВЫБОР по дуге
    sel_box = (118, 42, 192, 68)
    process(sel_box, lambda c: luma(c) < 110, "select", (12, 10, 8),
            lambda: arc_text("ВЫБОР", font("Arial Black.ttf", 10 * S), (153, 96), 45, 14.5, None, size))
    # PUSH -> ЖМИ (белое на чёрном)
    push_box = (141, 88, 163, 98)
    process(push_box, lambda c: luma(c) > 150 and c[0] > 150 and c[1] > 150 and c[2] > 150, "push", (240, 240, 240),
            lambda: pixel_mask(PUSH_GLYPHS, (144, 90), size), fill=(22, 14, 4))
    # CATHERINE -> КЭТРИН
    cat_box = (18, 10, 62, 21)
    process(cat_box, lambda c: luma(c) > 168, "cat", (196, 205, 140),
            lambda: word_mask_flat("КЭТРИН", font("Arial Bold.ttf", 8 * S), (20, 12, 60, 19), size))
    # записываем только изменившиеся пиксели
    ch = set()
    for (x, y) in touched:
        if rgb.getpixel((x, y)) != before.getpixel((x, y)):
            ch.add((x, y))
    paint_banks(rows, info, rgb, ch)
    out, changed, newt = ds_gfx.repack(d, info, rows)
    return d, out, before, rows, changed, newt


PUSH_GLYPHS = ["X.X.X X...X X...X",
               ".XXX. XX.XX X..XX",
               "..X.. X.X.X X.X.X",
               ".XXX. X...X XX..X",
               "X.X.X X...X X...X",
               "X.X.X X...X X...X"]


def pixel_mask(rows_txt, origin, size):
    """ручные пиксельные глифы (X = закрашено), для мелкой надписи PUSH"""
    big = Image.new("L", (size[0] * S, size[1] * S), 0)
    dr = ImageDraw.Draw(big)
    for j, line in enumerate(rows_txt):
        for i, ch in enumerate(line):
            if ch == "X":
                x, y = origin[0] + i, origin[1] + j
                dr.rectangle((x * S, y * S, x * S + S - 1, y * S + S - 1), fill=255)
    return big


def word_mask_flat(text, fnt, box, size):
    """текст растянут в прямоугольник box (x0,y0,x1,y1) по чернилам и высоте заглавных"""
    quad = [(box[0], box[1]), (box[2], box[1]), (box[2], box[3]), (box[0], box[3])]
    return word_layer(text, fnt, quad, size)


JOBS_EXTRA = {"katharune_01": make_katharune}

JOBS = {"save_edo01": job_edo01, "save_edo02": job_edo02, "save_sue01": job_sue01, "save_sue02": job_sue02}

JOBS.update(JOBS_EXTRA)

if __name__ == "__main__":
    names = sys.argv[1:] or list(JOBS)
    for n in names:
        d, out, before, rows, changed, newt = JOBS[n]()
        back = save_outputs(n, d, out, before, "2D/ue")
        ok = back == rows
        print(f"{n}: cells changed {changed}, new tiles {newt}, size {len(d)} -> {len(out)}, decode matches: {ok}")
