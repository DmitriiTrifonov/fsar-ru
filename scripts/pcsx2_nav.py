"""Навигация по меню PS2-игры в PCSX2 по снимкам: python3 -I scripts/pcsx2_nav.py request   (доходит до списка Request)
Классификация кадра по цветам: title («Press START button»), menu (оранжевые полосы справа), list (оранжевая полоса NEXT слева), other."""
import sys, os, time
sys.path.insert(0, os.path.dirname(__file__))
import pcsx2_ctl as C
from PIL import Image
TMP = C.ROOT / "dumps" / "pcsx2" / "_nav.png"
def px(im, x, y):  # координаты в системе 640x480
    return im.getpixel((int(x * im.width / 640), int(y * im.height / 480)))[:3]
def orange(c): return c[0] > 200 and 40 < c[1] < 140 and c[2] < 80
def classify():
    """title / menu (4 полосы справа) / list (есть полоса NEXT слева) / sub (1-3 полосы справа: Play Start, Option) / other"""
    C.shot(TMP); im = Image.open(TMP).convert("RGB")
    b = px(im, 340, 225)  # рамка «Press START»
    if 30 < b[0] < 110 and 60 < b[1] < 130 and 110 < b[2] < 190 and px(im, 590, 255)[2] > 100: return "title"
    bars = sum(orange(px(im, 610, y)) for y in (92, 145, 195, 247))
    left = orange(px(im, 30, 238)) or orange(px(im, 120, 238))
    if bars == 4 and left: return "list"
    if bars == 4: return "menu"
    if 1 <= bars <= 3 and orange(px(im, 610, 92)): return "sub"
    return "other"
def to_list(tries=40):
    """Дойти до списка Request. Курсор меню запоминается, поэтому по кругу: открыть пункт → если не Request, Cross и Down."""
    stage = 0
    for i in range(tries):
        k = classify(); print(i, k, flush=True)
        if k == "list": return True
        if k == "title": C.press("START", 200, 6000)
        elif k == "menu": C.press("CIRCLE", 250, 4500)
        elif k == "sub": C.press("CROSS", 250, 3500); C.press("DOWN", 300, 1500)
        elif stage % 2: C.press("CROSS", 250, 3500); stage += 1   # карта памяти (✕) / видео
        else: C.press("START", 200, 4000); stage += 1
    return False
# --- курсор главного меню по яркости полос (2026-11-09) ---
# Выбранная полоса пульсирует: то темнеет (~96 вместо 117-127), то светлеет (+10..+50). Остальные стоят на базе.
BARS = [(92, 480), (145, 520), (195, 570), (247, 600)]   # Play Start / Request / Movie / Option: y и начало x (640x480)
BASE = [117, 117, 119, 127]
def bar_dev(im):
    out = []
    for (y, x0), b in zip(BARS, BASE):
        v = [sum(px(im, x, yy)) / 3 for yy in (y - 10, y - 6, y + 6, y + 10) for x in range(x0, 636, 4)]
        out.append(sum(v) / len(v) - b)
    return out
def cursor(shots=3, thr=6):
    """Индекс подсвеченного пункта главного меню (0 Play Start, 1 Request, 2 Movie, 3 Option) или None.
    Берём несколько кадров (фаза пульсации), побеждает полоса с наибольшим |отклонением|."""
    best = [0.0] * 4
    for _ in range(shots):
        C.shot(TMP); d = bar_dev(Image.open(TMP).convert("RGB"))
        best = [b if abs(b) >= abs(x) else x for b, x in zip(best, d)]
        if max(abs(x) for x in best) > 4 * thr: break
    m = max(range(4), key=lambda i: abs(best[i]))
    return m if abs(best[m]) >= thr else None
def goto_item(idx, tries=12):
    """Подвести курсор главного меню на пункт idx (без нажатия Circle)."""
    for _ in range(tries):
        cur = cursor()
        print("cursor", cur, flush=True)
        if cur == idx: return True
        if cur is None: time.sleep(1.0); continue
        C.press("DOWN" if idx > cur else "UP", 150, 2500)
    return False
def open_request():
    """Из главного меню: курсор на Request, Circle."""
    if not goto_item(1): return False
    C.press("CIRCLE", 250, 4000); return True
if __name__ == "__main__":
    if sys.argv[1] == "cursor": print(cursor())
    if sys.argv[1] == "open_request": print("OK" if open_request() else "FAIL")
    if sys.argv[1] == "request": print("OK" if to_list() else "FAIL")
