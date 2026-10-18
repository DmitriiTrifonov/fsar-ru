"""Stage 4: Russian text for sprite labels (.pobj). stage4_labels.py [--preview] -> patched_raw/2D/.../*.pobj.z
Each label is drawn into the existing cell area (tiles of a cell are exclusive and there is no spare tile space), the style
(main font bold/normal, small font bold/normal) is picked automatically to fit the cell width."""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
import pobj_edit as E, fontio
from PIL import Image, ImageDraw

MAIN = fontio.Font("patched_raw/Chapter/Pack/Common/font.nftr")
SMALL = fontio.Font("patched_raw/2D/profile_font.NFTR")
STYLES = [(MAIN, 1, 1, "main+")]       # one tall bold style; wide words are squeezed horizontally to the cell (min scale MINSCALE)
MINSCALE = 0.62

# file -> {cell: text}
FREE = {
 "decoded/2D/KatharineSave.pobj": {19: "Играть", 20: "Назад", 21: "Запись", 22: "Загрузка", 23: "Удалить", 24: "Да", 25: "Нет",
                                    26: "Продолжить", 27: "Заказ", 28: "Далее", 29: "След. дни", 30: "Конец игры"},
 "decoded/2D/ue/katharine_obj.pobj": {36: ("Ответ окончательный?", dict(space=2, thresh=0.5, fg=4, align="center")),
                                      130: "Запись", 131: "Загрузка", 132: "Да", 133: "Нет", 134: ("Конец игры", dict(gap=(32, 5)))},
 "decoded/2D/ue/title_keyandmoji.pobj": {23: "Начать игру", 24: "Видео", 25: "Данные-01", 26: "Данные-02", 27: "Данные-03", 28: "Нет данных",
                                         29: "Назад", 30: "Загрузка", 31: "Копия", 32: "Удалить", 33: "Да", 34: "Нет", 35: "Продолжить",
                                         36: "Заказ", 37: "Далее", 57: "След. дни", 58: "Запись", 64: "Настройки", 65: "Справа", 66: "Слева",
                                         67: "Конец игры", 68: "Видео-00", 69: "Видео-01"},
}


BTN = dict(space=(1, 0), margin=2, gap=0)
BTN2 = dict(space=0, margin=1, gap=0, bold=0)
# boxed labels (frame is kept): file -> {cell: (lines, kwargs)}
BOXED = {
 "decoded/2D/ue/katharine_obj.pobj": {
   19: (["КЭТРИН"], {}),
   20: (["ПОДКЛЮЧЕНИЕ", "УПРАВЛЕНИЕ"], {}),
   21: (["УПРАВЛЕНИЕ", "ПУТЕВОДИТЕЛЕМ"], {}),
   22: (["УПРАВЛЕНИЕ НАБОРОМ"], {}),
   54: (["Назад"], BTN), 55: (["Назад"], BTN), 56: (["Выход"], BTN), 57: (["Выход"], BTN), 58: (["Смена"], BTN), 59: (["Смена"], BTN),
   60: (["Отмена"], BTN), 61: (["Отмена"], BTN), 62: (["Удалить"], BTN), 63: (["Удалить"], BTN),
   64: (["ЗАМЕТКИ"], {}), 65: (["СОХРАНЕНИЕ"], {}), 66: (["КОЛЛЕКЦИЯ"], {}),
   102: (["Заметки"], BTN2), 103: (["Заметки"], BTN2), 104: (["Возврат"], BTN2), 105: (["Возврат"], BTN2),
 },
 "decoded/2D/ue/pressstart.pobj": {c: (["Нажмите START"], dict(space=(3, 1), margin=4)) for c in range(4)},
 "decoded/2D/SubTitle.pobj": {0: (["Добро пожаловать в «Цветок, Солнце и Дождь»"], dict(bold=0, space=0, margin=3, gain=1.2)),
                              17: (["Убей прошлое"], dict(bold=0, space=(1, 0), margin=3, gain=1.2))},
}

# LED dot-matrix (cells 77/78 of katharine_obj): 3x3 dots on a 4 px pitch, 5x7 glyphs
LED = {
 "decoded/2D/ue/katharine_obj.pobj": {77: "ДА", 78: "НЕТ"},
}
# LED words of the lock-code screen (cells 33 BLANK, 34/35 HIT red/green): 4x4 dots on a 5 px pitch, 6x8 glyphs with 2-dot strokes
LED2 = {
 "decoded/2D/ue/katharine_obj.pobj": {33: ("МИМО", 2, 6), 34: ("ПОПАЛ", 2, 3), 35: ("ПОПАЛ", 3, 3)},
}
GLYPH6 = {
 "Д": [".#####", ".##.##", ".##.##", ".##.##", ".##.##", ".##.##", "######", "##..##"],
 "А": [".####.", "##..##", "##..##", "######", "##..##", "##..##", "##..##", "##..##"],
 "Н": ["##..##", "##..##", "##..##", "######", "##..##", "##..##", "##..##", "##..##"],
 "Е": ["######", "##....", "##....", "####..", "##....", "##....", "##....", "######"],
 "Т": ["######", "..##..", "..##..", "..##..", "..##..", "..##..", "..##..", "..##.."],
}
GLYPH6.update({
 "М": ["##...##", "###.###", "##.#.##", "##.#.##", "##...##", "##...##", "##...##", "##...##"],
 "И": ["##..##", "##..##", "##..##", "##.###", "###.##", "##..##", "##..##", "##..##"],
 "О": [".####.", "##..##", "##..##", "##..##", "##..##", "##..##", "##..##", ".####."],
})
# compact 3x7 glyphs (pitch 4, dot 3x3) for the narrow HIT cells
GLYPH3 = {
 "П": ["###", "#.#", "#.#", "#.#", "#.#", "#.#", "#.#"],
 "О": ["###", "#.#", "#.#", "#.#", "#.#", "#.#", "###"],
 "А": [".#.", "#.#", "#.#", "###", "#.#", "#.#", "#.#"],
 "Л": [".##", "#.#", "#.#", "#.#", "#.#", "#.#", "#.#"],
}
GLYPH5 = {
 "Д": [".####", ".#..#", ".#..#", ".#..#", ".#..#", "#####", "#...#"],
 "А": [".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"],
 "Н": ["#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"],
 "Е": ["#####", "#....", "#....", "####.", "#....", "#....", "#####"],
 "Т": ["#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."],
}
# tabs/icons with a text strip over a pattern: cell -> dict(rows=(y0,y1) text region, ref=row to copy as background | period=pattern period,
#   lines, font, bold, space, x=(x0,x1) allowed ink columns, fg, outline (None = background colour), clear=cols to level)
SM = SMALL
TABS = {
 "decoded/2D/ue/katharine_obj.pobj": {
   **{c: dict(rows=(13, 42), ref=12, lines=["ГИД"], font=MAIN, bold=1, space=1, x=(3, 36)) for c in (67, 68)},
   **{c: dict(rows=(21, 34), ref=20, lines=["ЗАМЕТКИ"], font=SM, bold=0, space=1, x=(3, 36)) for c in (69, 70)},
   **{c: dict(rows=(21, 34), period=13, solid=(3, 36), lines=["ВЕЩИ"], font=MAIN, bold=1, space=1, x=(3, 36)) for c in (71, 72)},
   **{c: dict(rows=(23, 35), ref=22, patch={34: 16, 35: 17}, lines=["ПОРТ"], font=SM, bold=1, space=0, x=(9, 30)) for c in (73, 74)},
   **{c: dict(rows=(15, 26), ref=28, lines=["ЗАПИСЬ"], font=MAIN, bold=0, space=0, x=(3, 36), level=(6, 33)) for c in (75, 76)},
   **{108: dict(rows=(3, 13), ref=1, lines=["ВЕРХ"], font=SM, bold=0, space=1, x=(1, 22), fg=3, outline=1),
      138: dict(rows=(1, 14), ref=0, lines=["СМЕНА"], font=SM, bold=0, space=0, x=(1, 22), fg=3, outline=1)},
 },
}


# flashing PUSH of the lock-code button (cell 39, 64x64): same 5x6 pixel glyphs as the ЖМИ in katharune_01.pbg
PUSH = {"decoded/2D/ue/katharine_obj.pobj": dict(ci=39, glyphs=["X.X.X X...X X...X", ".XXX. XX.XX X..XX", "..X.. X.X.X X.X.X",
                                                                 ".XXX. X...X XX..X", "X.X.X X...X X...X", "X.X.X X...X X...X"],
                                                  box=(22, 26, 42, 33), origin=(24, 27), fg=13, bg=1)}


def draw_push(p, ci, glyphs, box, origin, fg, bg):
    cv = p.canvas(ci)
    for y in range(box[1], box[3] + 1):
        for x in range(box[0], box[2] + 1): cv.px[y][x] = bg
    for j, line in enumerate(glyphs):
        for i, ch in enumerate(line):
            if ch == "X": cv.px[origin[1] + j][origin[0] + i] = fg
    p.set_canvas(ci, cv)


def draw_led(p, ci, text):
    cv = p.canvas(ci); H = len(GLYPH5["Д"])
    for y in range(cv.h):
        for x in range(cv.w):
            if cv.px[y][x] == 6: cv.px[y][x] = 1
    cols = []
    for k, ch in enumerate(text):
        if k: cols += [None] * (2 if len(text) < 3 else 1)
        cols += [[row[i] == "#" for row in GLYPH5[ch]] for i in range(5)]
    n = len(cols); x0 = (cv.w - (4 * n - 1)) // 2; y0 = 13
    for c, col in enumerate(cols):
        if col is None: continue
        for r in range(H):
            if col[r]:
                for dy in range(3):
                    for dx in range(3): cv.px[y0 + 4 * r + dy][x0 + 4 * c + dx] = 6
    p.set_canvas(ci, cv)


def draw_led2(p, ci, text, lit, gw=6):
    cv = p.canvas(ci); cols = []
    G = GLYPH6 if gw == 6 else GLYPH3
    px, dx_, py, dy_, rows = (5, 4, 5, 4, 8) if gw == 6 else (4, 3, 5, 4, 7)    # narrow glyphs: dots 3x4 on a 4x5 pitch
    for k, ch in enumerate(text):
        if k: cols += [None] * (2 if gw == 6 else 1)
        cols += [[row[i] == "#" for row in G[ch]] for i in range(len(G[ch][0]))]
    nd = cv.w // px; c0 = (nd - len(cols)) // 2; y0 = (cv.h - rows * py) // 2
    for y in range(cv.h):
        for x in range(cv.w):
            if cv.px[y][x] is not None: cv.px[y][x] = 0
    for c, col in enumerate(cols):
        if col is None: continue
        for r in range(rows):
            if col[r]:
                for dy in range(dy_):
                    for dx in range(dx_): cv.px[y0 + py * r + 1 + dy][px * (c0 + c) + 1 + dx] = lit
    p.set_canvas(ci, cv)


def draw_tab(p, ci, rows, lines, font, bold, space, x, ref=None, period=None, fg=5, outline=None, level=(), gap=1, solid=None, patch=None):
    cv = p.canvas(ci); y0, y1 = rows
    orig = [r[:] for r in cv.px]
    for y in range(y0, y1 + 1):
        for xx in range(cv.w):
            if cv.px[y][xx] is None: continue
            if period: cv.px[y][xx] = orig[y - period * ((y - y0) // period + 1)][xx]
            else:
                cv.px[y][xx] = orig[ref][xx]
                if xx in level: cv.px[y][xx] = orig[ref][10]
    for y, sy in (patch or {}).items():
        for xx in range(cv.w):
            if cv.px[y][xx] is not None: cv.px[y][xx] = orig[sy][xx]
    if solid:
        sv = orig[5][5]
        for y in range(y0, y1 + 1):
            for xx in range(solid[0], solid[1] + 1):
                if cv.px[y][xx] is not None: cv.px[y][xx] = sv
    bgi = outline if outline is not None else (orig[5][5] if period else orig[ref][20])
    bank = p.cells[ci][0]["bank"]; pal = [p.pal[bank * 16 + i] for i in range(16)]
    maxw = x[1] - x[0] + 1; covs = []
    for t in lines:
        cov, w = E.text_coverage(t, font, bold, space)
        if w > maxw: cov, w = E.squeeze(cov, w, maxw)
        ink = [yy for yy in range(len(cov)) if any(cov[yy])]; covs.append((cov[min(ink):max(ink) + 1], w))
    total = sum(len(c) for c, _ in covs) + gap * (len(covs) - 1)
    yy0 = y0 + ((y1 - y0 + 1) - total) // 2
    for cov, w in covs:
        xx0 = x[0] + (maxw - w) // 2; h = len(cov)
        def get(a, b): return cov[a][b] if 0 <= a < h and 0 <= b < w else 0
        for a in range(-1, h + 1):
            for b in range(-1, w + 1):
                Y, X = yy0 + a, xx0 + b
                if not (0 <= Y < cv.h and 0 <= X < cv.w) or cv.px[Y][X] is None: continue
                c = get(a, b)
                if c >= 0.55: cv.px[Y][X] = fg
                elif c >= 0.2:
                    tgt = tuple(int(pal[bgi][k] + (pal[fg][k] - pal[bgi][k]) * c / 0.55) for k in range(3)); cv.px[Y][X] = E.nearest(pal, tgt)
                elif any(get(a + da, b + db) >= 0.35 for da in (-1, 0, 1) for db in (-1, 0, 1)): cv.px[Y][X] = bgi
        yy0 += h + gap
    p.set_canvas(ci, cv); return cv


def fit(text, width, opts=None):
    """-> (font, bold, space, name, w, scale). Default style is bold; if it would need a squeeze below 0.58 the thin tight style is tried."""
    opts = opts or {}
    font = opts.get("font", MAIN)
    cands = [(opts.get("bold", 1), opts.get("space", 1))]
    if "bold" not in opts: cands.append((0, 0))
    best = None
    for bold, space in cands:
        cov, w = E.text_coverage(text, font, bold, space)
        sc = min(1.0, width / w)
        if best is None or (best[5] < 0.58 and sc > best[5]): best = (font, bold, space, "b%d s%d" % (bold, space), min(w, width), sc)
        if sc >= 0.58: break
    return best


def run(preview=True):
    sheet = []
    for path in list(dict.fromkeys(list(FREE) + list(BOXED) + list(LED) + list(LED2) + list(TABS) + list(PUSH))):
        p = E.Pobj(path)
        for ci, text in FREE.get(path, {}).items():
            opts = {}
            if isinstance(text, tuple): text, opts = text
            cv = p.canvas(ci); font, bold, space, name, w, sc = fit(text, cv.w, opts)
            if sc < MINSCALE: print("УЗКО:", path, ci, text, "scale", round(sc, 2))
            before = p.render(ci, 3)
            kw = dict(bold=bold, space=space, align=opts.get("align", "left"), maxw=cv.w)
            for k in ("thresh", "fg"):
                if k in opts: kw[k] = opts[k]
            if "gap" in opts:   # cell with a hole in its OAM layout: one word on each side of the hole
                gs, gl = opts["gap"]; used = sorted({v for r in cv.px for v in r if v}); pal = [p.pal[p.cells[ci][0]["bank"] * 16 + i] for i in range(16)]
                kw["fg"] = max(used, key=lambda i: sum(pal[i])); kw["bg"] = min(used, key=lambda i: sum(pal[i])); kw["bold"] = 0; kw["space"] = 0
                for part, x0, wd in zip(text.split(" ", 1), (0, gs + gl), (gs, cv.w - gs - gl)):
                    vc = E.Canvas([], wd, cv.h, 0, 0); vc.px = [[0] * wd for _ in range(cv.h)]; kw["maxw"] = wd
                    E.draw_text(p, ci, vc, part, font, **kw)
                    for y in range(cv.h):
                        for x in range(wd):
                            if cv.px[y][x0 + x] is not None: cv.px[y][x0 + x] = vc.px[y][x]
            else: E.draw_text(p, ci, cv, text, font, **kw)
            p.set_canvas(ci, cv)
            sheet.append((f"{os.path.basename(path)[:10]} {ci} {text} [{name} scale {sc:.2f}]", before, p.render(ci, 3)))
        for ci, (lines, kw) in BOXED.get(path, {}).items():
            kw = dict(kw); font = kw.pop("font", MAIN)
            cv = p.canvas(ci); before = p.render(ci, 3)
            E.draw_boxed(p, ci, cv, lines, font, **kw); p.set_canvas(ci, cv)
            sheet.append((f"{os.path.basename(path)[:10]} {ci} {' / '.join(lines)}", before, p.render(ci, 3)))
        for ci, text in LED.get(path, {}).items():
            before = p.render(ci, 3); draw_led(p, ci, text)
            sheet.append((f"{os.path.basename(path)[:10]} {ci} LED {text}", before, p.render(ci, 3)))
        for ci, (text, lit, gw) in LED2.get(path, {}).items():
            before = p.render(ci, 3); draw_led2(p, ci, text, lit, gw)
            sheet.append((f"{os.path.basename(path)[:10]} {ci} LED2 {text}", before, p.render(ci, 3)))
        for ci, kw in TABS.get(path, {}).items():
            before = p.render(ci, 3); draw_tab(p, ci, **kw)
            sheet.append((f"{os.path.basename(path)[:10]} {ci} tab {' / '.join(kw['lines'])}", before, p.render(ci, 3)))
        if path in PUSH:
            kw = PUSH[path]; before = p.render(kw["ci"], 3); draw_push(p, **kw)
            sheet.append((f"{os.path.basename(path)[:10]} {kw['ci']} PUSH->ЖМИ", before, p.render(kw["ci"], 3)))
        rel = path.replace("decoded/", "patched_raw/") + ".z"
        p.save_z(rel); print("saved", rel)
    if preview:
        W = 2 * max(max(b.width, a.width) for _, b, a in sheet) + 20; H = sum(max(b.height, a.height) + 14 for _, b, a in sheet)
        im = Image.new("RGB", (W, H), (60, 60, 90)); dr = ImageDraw.Draw(im); y = 0
        for name, b, a in sheet:
            dr.text((0, y), name, fill=(255, 255, 0)); y += 12; im.paste(b, (0, y)); im.paste(a, (W // 2 + 10, y)); y += max(b.height, a.height) + 2
        im.save("dumps/gfx/pobj/labels_preview.png"); print("preview -> dumps/gfx/pobj/labels_preview.png")
        # split preview: only the second batch (katharine_obj tabs / LED etc.)
        keep = [t for t in sheet if any(k in t[0] for k in ("katharine_", "pressstart", "SubTitle"))]
        W = 2 * max(max(b.width, a.width) for _, b, a in keep) + 20; H = sum(max(b.height, a.height) + 14 for _, b, a in keep)
        im = Image.new("RGB", (W, H), (60, 60, 90)); dr = ImageDraw.Draw(im); y = 0
        for name, b, a in keep:
            dr.text((0, y), name, fill=(255, 255, 0)); y += 12; im.paste(b, (0, y)); im.paste(a, (W // 2 + 10, y)); y += max(b.height, a.height) + 2
        im.save("dumps/gfx/pobj/labels_preview2.png")


if __name__ == "__main__":
    run()
