"""Прогулка по диалогу в PCSX2: N раз нажать подтверждение и снять кадр. python3 -I scripts/pcsx2_walk.py <префикс> <N> [кнопка=CIRCLE] [пауза_мс=1500]
Кадры: dumps/pcsx2/walk/<префикс>_NNN.png (полные) и _s.png (640x480). Контактный лист: --sheet <префикс>."""
import sys, os
from pathlib import Path
sys.path.insert(0, os.path.dirname(__file__))
import pcsx2_ctl as C
from PIL import Image
OUT = C.ROOT / "dumps" / "pcsx2" / "walk"
def sheet(prefix, cols=3, w=640):
    fs = sorted(OUT.glob(f"{prefix}_*_s.png")); h = 480
    rows = (len(fs) + cols - 1) // cols
    im = Image.new("RGB", (cols * w, rows * h))
    for i, f in enumerate(fs): im.paste(Image.open(f), ((i % cols) * w, (i // cols) * h))
    p = OUT / f"{prefix}_sheet.png"; im.save(p); return p
if __name__ == "__main__":
    if sys.argv[1] == "--sheet": print(sheet(sys.argv[2])); sys.exit()
    prefix, n = sys.argv[1], int(sys.argv[2]); btn = sys.argv[3] if len(sys.argv) > 3 else "CIRCLE"; pause = int(sys.argv[4]) if len(sys.argv) > 4 else 1500
    OUT.mkdir(parents=True, exist_ok=True)
    for i in range(n):
        C.press(btn, 400, pause)
        f = OUT / f"{prefix}_{i:03d}.png"; C.shot(f)
        Image.open(f).convert("RGB").resize((640, 480)).save(OUT / f"{prefix}_{i:03d}_s.png"); print(i, flush=True)
