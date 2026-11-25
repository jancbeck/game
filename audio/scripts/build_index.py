#!/usr/bin/env python3
"""Write audio/index.html: HTML5 players grouped by item, models side by side.

Reads prompts.json, the JSON sidecars next to each take and norm/_levels.csv.
Players use the normalized (-16 LUFS) files; every player also links the original.
Run: python3 audio/scripts/build_index.py
"""
import csv
import html
import json
from pathlib import Path

AUDIO = Path(__file__).resolve().parent.parent
P = json.loads((AUDIO / "prompts.json").read_text())

SFX_MODELS = [("A", "Stable Audio 3", "sfx/stable-audio-3"), ("B", "MOSS-SoundEffect v2", "sfx/moss")]


def levels(folder):
    f = AUDIO / folder / "norm" / "_levels.csv"
    if not f.exists():
        return {}
    with f.open() as fh:
        return {r["file"]: r for r in csv.DictReader(fh)}


def e(s):
    return html.escape(str(s))


def meta_line(m, keys):
    parts = []
    for k, label in keys:
        if m.get(k) is not None:
            parts.append(f"{label} {e(m[k])}")
    return " · ".join(parts)


def player(folder, name, lv, label, meta, keys, note=""):
    wav = AUDIO / folder / name
    if not wav.exists():
        return ""
    norm = AUDIO / folder / "norm" / name
    src = f"{folder}/norm/{name}" if norm.exists() else f"{folder}/{name}"
    row = lv.get(name, {})
    lvl = f" · {e(row['lufs_before'])} LUFS before" if row else ""
    return (f'<div class="take"><div class="tl">{e(label)}{note}</div>'
            f'<audio controls preload="none" src="{e(src)}"></audio>'
            f'<div class="tm">{meta_line(meta, keys)}{lvl} · '
            f'<a href="{e(folder)}/{e(name)}">original</a></div></div>')


def column(letter, model, folder, item_id, takes, loop, keys, prompt_html):
    lv = levels(folder)
    body = []
    for k in range(1, takes + 1):
        stem = f"{item_id}_t{k}" if takes > 0 else item_id
        side = AUDIO / folder / f"{stem}.json"
        meta = json.loads(side.read_text()) if side.exists() else {}
        body.append(player(folder, f"{stem}.wav", lv, f"take {k}", meta, keys))
        if loop:
            body.append(player(folder, f"{stem}_loop.wav", lv, f"take {k} loop", meta, keys,
                               ' <span class="chip">seamless loop</span>'))
    body = "".join(b for b in body if b)
    if not body:
        body = '<div class="missing">not generated (see README)</div>'
    return (f'<div class="col"><h4><span class="badge">{letter}</span> {e(model)}</h4>'
            f'{prompt_html}{body}</div>')


def sfx_cards():
    out = []
    keys = [("seconds", "len"), ("cfg", "cfg"), ("steps", "steps"), ("seed", "seed"),
            ("wall_seconds", "render s")]
    for it in P["sfx"]:
        cols = []
        for letter, model, folder in SFX_MODELS:
            side = AUDIO / folder / f"{it['id']}_t1.json"
            m = json.loads(side.read_text()) if side.exists() else {}
            neg = m.get("negative_prompt")
            ph = (f'<p class="prompt">{e(m.get("prompt") or it["sa3"]["prompt"])}</p>'
                  + (f'<p class="neg">negative: {e(neg)}</p>' if neg else ""))
            cols.append(column(letter, model, folder, it["id"], 2, it.get("loop"), keys, ph))
        out.append(f'<section class="card" id="{e(it["id"])}"><h3>{e(it["title"])} '
                   f'<span class="chip">{e(it["kind"])}</span></h3>'
                   f'<p class="desc">{e(it["desc"])}</p><div class="cols">{"".join(cols)}</div>'
                   f'</section>')
    return "\n".join(out)


CSS = """
:root{--bg:#f6f5f2;--fg:#1d1f23;--mut:#5f6570;--card:#fff;--line:#dcd9d2;--acc:#2d5a7b;--chip:#e8edf1}
@media(prefers-color-scheme:dark){:root{--bg:#14171b;--fg:#e6e8ea;--mut:#98a1ab;--card:#1c2026;--line:#2c333b;--acc:#7fb2d6;--chip:#27303a}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,-apple-system,Segoe UI,sans-serif}
main{max-width:1180px;margin:0 auto;padding:24px 16px 64px}
h1{font-size:26px;margin:0 0 4px}h2{font-size:20px;margin:40px 0 12px;border-bottom:1px solid var(--line);padding-bottom:6px}
h3{font-size:17px;margin:0 0 2px}h4{font-size:14px;margin:0 0 6px}
.lead{color:var(--mut);margin:0 0 16px;max-width:70ch}
nav{display:flex;flex-wrap:wrap;gap:6px;margin:12px 0}
nav a{background:var(--chip);color:var(--fg);text-decoration:none;padding:3px 10px;border-radius:12px;font-size:13px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 16px;margin:12px 0}
.desc{color:var(--mut);margin:0 0 10px;font-size:14px}
.cols{display:grid;grid-template-columns:1fr 1fr;gap:16px}
@media(max-width:760px){.cols{grid-template-columns:1fr}}
.col{min-width:0}
.badge{display:inline-block;background:var(--acc);color:var(--bg);border-radius:4px;padding:0 6px;font-weight:600;margin-right:4px}
.chip{display:inline-block;background:var(--chip);color:var(--mut);border-radius:10px;padding:0 8px;font-size:12px;font-weight:400}
.prompt{margin:0 0 4px;font-size:13px}
.neg{margin:0 0 8px;font-size:12px;color:var(--mut)}
.take{margin:6px 0 10px}.tl{font-size:12px;color:var(--mut)}
audio{width:100%;height:36px}
.tm{font-size:12px;color:var(--mut)}.tm a{color:var(--acc)}
.missing{font-size:13px;color:var(--mut);border:1px dashed var(--line);border-radius:6px;padding:8px}
"""


def main():
    nav = "".join(f'<a href="#{e(i["id"])}">{e(i["id"])}</a>' for i in P["sfx"])
    page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Courtyard audio A/B</title><style>{CSS}</style></head>
<body><main>
<h1>Courtyard audio A/B</h1>
<p class="lead">{e(P["scene"])} Every player is normalized to about -16 LUFS so the models compare at equal loudness; the original file is linked under each player. A is Stable Audio 3, B is MOSS-SoundEffect v2.</p>
<nav>{nav}</nav>
<h2>Sound effects</h2>
{sfx_cards()}
</main></body></html>
"""
    (AUDIO / "index.html").write_text(page)
    print("wrote", AUDIO / "index.html")


if __name__ == "__main__":
    main()
