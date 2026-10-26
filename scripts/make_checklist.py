"""Phone checklist: make_checklist.py [docs/check-3ds.tsv] [build/phone/check-3ds.html]
TSV columns: scene, speaker, line (\\n = line break), what to check. One self-contained HTML file with tick boxes
(ticks stay in the phone browser). Only Russian text goes in: the file is safe to commit."""
import csv, html, os, sys, datetime
src = sys.argv[1] if len(sys.argv) > 1 else "docs/check-3ds.tsv"
out = sys.argv[2] if len(sys.argv) > 2 else "build/phone/check-3ds.html"
rows = list(csv.reader(open(src, encoding="utf-8"), delimiter="\t"))[1:]
items = []
for n, (scene, who, text, check) in enumerate(r for r in rows if len(r) >= 4):
    t = "<br>".join(html.escape(x) for x in text.split("\\n"))
    items.append(f'<label class="it"><input type="checkbox" data-k="{n}"><div><div class="sc">{html.escape(scene)} · {html.escape(who)}</div>'
                 f'<div class="tx">{t}</div><div class="ck">{html.escape(check)}</div></div></label>')
page = f"""<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Проверка на 3DS</title><style>
:root{{--bg:#fff;--fg:#1c1c1e;--mut:#6b6b70;--bd:#d8d8dc;--ac:#0a6cff}}
@media(prefers-color-scheme:dark){{:root{{--bg:#111;--fg:#f0f0f2;--mut:#9a9aa0;--bd:#333;--ac:#4d9bff}}}}
body{{margin:0;padding:16px;background:var(--bg);color:var(--fg);font:17px/1.4 -apple-system,system-ui,sans-serif}}
h1{{font-size:20px;margin:0 0 4px}}.m{{color:var(--mut);font-size:14px;margin-bottom:14px}}
.it{{display:flex;gap:12px;padding:12px 0;border-top:1px solid var(--bd)}}input{{width:26px;height:26px;flex:none;accent-color:var(--ac)}}
.sc{{color:var(--mut);font-size:13px}}.tx{{font-size:19px;margin:4px 0;font-weight:600}}.ck{{font-size:14px;color:var(--mut)}}
input:checked+div{{opacity:.45}}</style></head><body>
<h1>Проверка на 3DS</h1><div class="m">{datetime.date.today():%d.%m.%Y} · отметок: <span id="n">0</span> из {len(items)}</div>
{"".join(items)}
<script>
var K="fsar-check-"+document.title,s={{}};try{{s=JSON.parse(localStorage.getItem(K)||"{{}}")}}catch(e){{}}
var b=document.querySelectorAll("input");
function c(){{document.getElementById("n").textContent=document.querySelectorAll("input:checked").length}}
b.forEach(function(x){{x.checked=!!s[x.dataset.k];x.onchange=function(){{s[x.dataset.k]=x.checked;try{{localStorage.setItem(K,JSON.stringify(s))}}catch(e){{}};c()}}}});c();
</script></body></html>"""
os.makedirs(os.path.dirname(out), exist_ok=True)
open(out, "w", encoding="utf-8").write(page); print(f"{len(items)} пунктов -> {out}")

# plain text for pasting into a messenger (☐ boxes)
txt = os.path.splitext(out)[0] + ".txt"
lines = [f"Проверка на 3DS, {datetime.date.today():%d.%m.%Y}", ""]
for scene, who, text, check in (r for r in rows if len(r) >= 4):
    lines += [f"☐ {scene} · {who}", "«" + text.replace("\\n", " / ") + "»", f"   → {check}", ""]
open(txt, "w", encoding="utf-8").write("\n".join(lines).rstrip() + "\n"); print(f"-> {txt}")
