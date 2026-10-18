"""gfx_render.py Guide <page>|--all [--check]: draw the Russian of text/gfx/Guide/<page>.tsv (id<TAB>EN<TAB>RU per block, ids from gfx_extract)
over the English text and write patched_raw/Guide/ue/<page>.pbg.z. --check only reports whether every block fits (no output file)."""
import sys, os, glob
sys.path.insert(0, os.path.dirname(__file__))
import gfx_blocks as G, gfx_extract as X, gfx_font as F, gfx_lines as GL, ds_gfx, lz10

ROOT = G.ROOT; PITCH = 11; INK = 2; BULLET_SKIP = 10

def wrap(text, first_w, w, n):
    words = text.split(); lines = []; cur = ""; lim = first_w
    for wd in words:
        t = (cur + " " + wd).strip()
        if F.width(t) <= lim or not cur: cur = t
        else: lines.append(cur); cur = wd; lim = w
    if cur: lines.append(cur)
    return lines

def load_spec(kind, name):
    p = f"{ROOT}/text/gfx/{kind}/{name}.tsv"; spec = {}
    if os.path.exists(p):
        for ln in open(p, encoding="utf-8"):
            f = ln.rstrip("\n").split("\t")
            if len(f) >= 3 and f[0].isdigit() and f[2].strip(): spec[int(f[0])] = (f[1], f[2].strip())
    return spec

# last line of a long essay that the block splitter attached to the picture below: (y0, y1, x0, x1) to clear
LEFTOVER = {"m_guide40": [(785, 794, 0, 56)], "m_guide36": [(320, 322, 0, 255)]}   # m_guide36: dot of the "i" of the last English line

def render(kind, name, write=True):
    d, info, rows = G.load(kind, name); out = [r[:] for r in rows]; W = len(rows[0]); spec = load_spec(kind, name); report = []
    blist = X.blocks(rows)
    for i in range(len(blist) - 1):    # RU "<<" on block i+1: its ink belongs to block i (a line cut in two by the line splitter)
        if i + 1 in spec and spec[i + 1][1] == "<<" and i in spec:
            a, c = blist[i], blist[i + 1]
            a["y0"] = min(a["y0"], c["y0"]); a["y1"] = max(a["y1"], c["y1"]); a["left"] = min(a["left"], c["left"]); a["right"] = max(a["right"], c["right"])
            a["r0"] = a["y0"]; a["n"] = 1; a["lines"] = [dict(a["lines"][0], y0=a["y0"], y1=a["y1"])]
            del spec[i + 1]
    for i, b in enumerate(blist):
        if i not in spec: continue
        en, ru = spec[i]
        miss = F.missing(ru)
        if b["n"] == 1 and en.isupper() and b["y1"] - b["y0"] <= 8: b["r0"] = b["y0"]   # all-caps line (8 rows of ink): cap top = ink top, not base - 2
        elif b["n"] == 1 and 0 < b["r0"] - b["y0"] <= 6 and en.startswith(("[", "(")): b["r0"] = b["y0"]   # bracketed caption: the base-2 estimate lands below the top of the ink
        if b["n"] > 1:   # list of lines that all have a leader: RU is "line | line | ..."
            infos = []
            for k, l in enumerate(b["lines"]):
                l["r0"] = b["r0"] + PITCH * k; infos.append(GL.analyse(rows, l, strict=True, dotted_ok=name in ("m_guide31",)))
            if all(a["xs"] is not None for a in infos):
                parts = [t.strip() for t in ru.split("|")]
                if len(parts) != b["n"]: report.append((i, False, len(parts), b["n"], [])); continue
                for l, a, t in zip(b["lines"], infos, parts):
                    ok, w, lim = GL.fits(l, a, t, W); report.append((i, ok, w, lim, F.missing(t))); GL.draw_item(out, l, a, t, b["color"])
                continue
        if b["n"] == 1:
            l = b["lines"][0]; l["r0"] = b["r0"]; a = GL.analyse(rows, l, strict=True, dotted_ok=name in ("m_guide31",))
            if a["xs"] is not None:
                ok, w, lim = GL.fits(l, a, ru, W); report.append((i, ok, w, lim, miss))
                GL.draw_item(out, l, a, ru, b["color"]); continue
        left, right, n = b["left"], max(b["right"], b["left"] + 60), b["n"]
        x_first = left + b["indent"] + (BULLET_SKIP if b["bullet"] else 0)
        # wide headings may use the whole page width
        limit = right if n > 1 else min(W - 4, max(right, left + int(F.width(ru))))
        lines = wrap(ru, limit - x_first + 1, limit - left + 1, n)
        ok = len(lines) <= n and not miss and all(F.width(l) <= (limit - (x_first if k == 0 else left) + 1) for k, l in enumerate(lines))
        report.append((i, ok, len(lines), n, miss))
        # erase old ink of the block (keep the bullet square)
        for y in range(b["y0"], b["y1"] + 1):
            for x in range(left, right + 2):
                if b["bullet"] and x < b["lines"][0]["x0"] + 8 and y <= b["lines"][0]["y1"]: continue
                if 0 <= x < W: out[y][x] = 0
        for k, l in enumerate(lines[:n]):
            def put(x, y):
                if 0 <= x < W and 0 <= y < len(out): out[y][x] = b["color"]
            F.draw(l, put, x_first if k == 0 else left, b["r0"] + k * PITCH)
    for y0, y1, x0, x1 in LEFTOVER.get(name, []):
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1): out[y][x] = 0
    if write and all(ok for _, ok, *_ in report):
        nd, changed, _ = ds_gfx.repack(d, info, out)
        path = f"{ROOT}/patched_raw/{kind}/ue/{name}.pbg.z"; os.makedirs(os.path.dirname(path), exist_ok=True)
        open(path, "wb").write(lz10.compress(nd))
    return report

if __name__ == "__main__":
    kind = sys.argv[1]; names = [sys.argv[2]] if sys.argv[2] != "--all" else sorted(os.path.basename(f)[:-4] for f in glob.glob(f"{ROOT}/text/gfx/{kind}/*.tsv") if not f.endswith(".lines.tsv"))
    for nm in names:
        rep = render(kind, nm, write="--check" not in sys.argv)
        bad = [r for r in rep if not r[1]]
        print(nm, "blocks", len(rep), "BAD" if bad else "ok", [(i, f"{a}/{n}" if not miss else f"missing {miss}") for i, ok, a, n, miss in bad])
