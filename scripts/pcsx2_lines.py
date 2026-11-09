"""Пройти диалог в PCSX2 и сохранить только кадры с новой репликой: python3 -I scripts/pcsx2_lines.py <префикс> <макс_реплик> [пауза_мс=2500]
Новая реплика = изменилась обрезка окна диалога (низ кадра). Кадры: dumps/pcsx2/walk/<префикс>_NNN_s.png; лист: pcsx2_walk.py --sheet <префикс>."""
import sys, os, time
sys.path.insert(0, os.path.dirname(__file__))
import pcsx2_ctl as C
from PIL import Image, ImageChops
OUT = C.ROOT / "dumps" / "pcsx2" / "walk"; TMP = OUT / "_t.png"
def snap():
    C.shot(TMP); im = Image.open(TMP).convert("RGB").resize((640, 480)); return im, im.convert("L").crop((10, 400, 215, 470))  # только текст: без портрета справа и «on air»
if __name__ == "__main__":
    prefix, n = sys.argv[1], int(sys.argv[2]); pause = int(sys.argv[3]) if len(sys.argv) > 3 else 2500
    OUT.mkdir(parents=True, exist_ok=True)
    im, last = snap(); k = 0; stuck = 0
    im.save(OUT / f"{prefix}_{k:03d}_s.png")
    while k + 1 < n and stuck < 4:
        C.press("CIRCLE", 400, pause)
        im, cur = snap()
        diff = ImageChops.difference(last, cur).convert("L").point(lambda v: 255 if v > 40 else 0).getbbox()
        if diff:
            k += 1; stuck = 0; last = cur; im.save(OUT / f"{prefix}_{k:03d}_s.png"); print("line", k, flush=True)
        else: stuck += 1
    print("done", k + 1, "lines, stuck", stuck)
