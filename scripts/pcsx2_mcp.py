"""MCP-сервер: PCSX2 (PS2) для проверки русификатора японской версии. Запускает Claude Code по stdio (см. .mcp.json).
Свой экземпляр PCSX2 с изолированным профилем (build/pcsx2-profile), настройки пользователя не трогает. Детали: scripts/pcsx2_ctl.py.
Tools: pcsx2_open, pcsx2_press, pcsx2_screenshot, pcsx2_read_mem, pcsx2_find, pcsx2_dump_state, pcsx2_load_state, pcsx2_status, pcsx2_quit."""
import io, os, struct, sys, time
from pathlib import Path
from mcp.server.fastmcp import FastMCP, Image
from PIL import Image as PILImage

sys.path.insert(0, os.path.dirname(__file__))
import pcsx2_ctl as C

ROOT = C.ROOT
mcp = FastMCP("fsar-pcsx2")


@mcp.tool()
def pcsx2_open(iso: str = "build/ps2/rel.iso", state: str = "") -> str:
    """Запустить (или перезапустить) свой экземпляр PCSX2 с образом (путь от корня проекта) и, если нужно, состоянием .p2s. Ждёт, пока ответит PINE."""
    return C.open_game(ROOT / iso, (ROOT / state) if state else None)


@mcp.tool()
def pcsx2_press(buttons: str, hold_ms: int = 120, wait_ms: int = 800) -> str:
    """Нажать кнопки PS2: CROSS (A, X), CIRCLE (B), TRIANGLE, SQUARE, START, SELECT, UP, DOWN, LEFT, RIGHT, L1, R1, L2, R2; комбинация через +. Держит hold_ms, отпускает, ждёт wait_ms (реальное время, эмулятор идёт сам)."""
    return C.press(buttons, hold_ms, wait_ms)


@mcp.tool()
def pcsx2_screenshot(scale: float = 0.5) -> Image:
    """Снимок кадра игры (F8 PCSX2, около 3-8 с); scale уменьшает (по умолчанию 0.5 → 852 px)."""
    f = C.shot(ROOT / "dumps" / "pcsx2" / "_mcp_shot.png")
    im = PILImage.open(f).convert("RGB")
    if scale != 1: im = im.resize((int(im.width * scale), int(im.height * scale)), PILImage.LANCZOS)
    buf = io.BytesIO(); im.save(buf, "PNG")
    return Image(data=buf.getvalue(), format="png")


@mcp.tool()
def pcsx2_read_mem(addr: str, length: int = 64) -> str:
    """Прочитать память EE (адрес hex, 0..0x01FFFFFF) из живой игры через PINE, hex-дамп."""
    return C.read_mem(int(addr, 16), int(length)).hex()


@mcp.tool()
def pcsx2_find(pattern_hex: str, start: str = "0x100000", length: int = 0x400000) -> str:
    """Найти последовательность байт (hex) в EE RAM диапазона [start, start+length) через PINE (медленно: ~1 МБ/с). Для всей памяти лучше pcsx2_dump_state."""
    pat = bytes.fromhex(pattern_hex); a = int(start, 16); res = []
    chunk = 0x40000
    for off in range(0, length, chunk):
        d = C.read_mem(a + off, min(chunk + len(pat), a + length - (a + off)))
        i = d.find(pat)
        while i >= 0 and i < chunk:
            res.append(hex(a + off + i)); i = d.find(pat, i + 1)
    return "\n".join(res) or "не найдено"


@mcp.tool()
def pcsx2_dump_state(name: str, slot: int = 9) -> str:
    """Сохранить состояние и выгрузить в dumps/pcsx2/<name>/: state.p2s, eeMemory.bin (32 МБ), GS.bin (видеопамять, 4 МБ+). Дальше искать в файлах скриптами."""
    return "\n".join(C.dump_state(ROOT / "dumps" / "pcsx2" / name, slot))


@mcp.tool()
def pcsx2_load_state(slot: int) -> str:
    """Загрузить состояние из слота профиля (PINE); состояния пользователя из ~/Library/.../PCSX2/sstates открывать через pcsx2_open(state=...)."""
    return C.load_state(slot)


@mcp.tool()
def pcsx2_status() -> str:
    """0 идёт, 1 пауза, 2 нет игры; название игры."""
    return f"{C.pine_status()} {C.title()}"


@mcp.tool()
def pcsx2_quit() -> str:
    """Закрыть свой экземпляр PCSX2 (пользовательский не трогает)."""
    return C.quit_game()


if __name__ == "__main__":
    mcp.run()
