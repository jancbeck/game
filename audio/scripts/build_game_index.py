#!/usr/bin/env python3
"""Write audio/game.html: contact sheet of the game sounds in game/data/sounds.json.

Players use audio/sfx/game/final/ (same files as game/assets/audio/). A "walk" button
per surface plays random steps at the game's step interval, at the proposed footstep
level over the rain bed at its proposed level, so repetition and balance can be heard.
Notes per sound come from audio/sfx/game/_notes.json.
Run: python3 audio/scripts/build_game_index.py
"""
import csv
import html
import json
from pathlib import Path

AUDIO = Path(__file__).resolve().parent.parent
ROOT = AUDIO.parent
FINAL = "sfx/game/final"
S = json.loads((ROOT / "game" / "data" / "sounds.json").read_text())
NOTES = json.loads((AUDIO / "sfx" / "game" / "_notes.json").read_text())
PROMPTS = {i["id"]: i for i in json.loads((AUDIO / "prompts.json").read_text())["game_sfx"]}


def e(s):
    return html.escape(str(s))


def levels():
    rows = {}
    f = AUDIO / FINAL / "_levels.tsv"
    if f.exists():
        for r in csv.reader(f.open(), delimiter="\t"):
            rows[r[0]] = r
    return rows


LV = levels()


def rel(asset):
    """assets/audio/x/y.wav -> sfx/game/final/x/y.wav"""
    return f"{FINAL}/{asset.removeprefix('assets/audio/')}"


def player(asset, label=None):
    key = asset.removeprefix("assets/audio/")
    r = LV.get(key)
    lv = f" · {e(r[2])} s · {e(r[3])} LUFS · TP {e(r[4])} dB · from {e(r[1])}" if r else ""
    return (f'<div class="take"><div class="tl">{e(label or Path(asset).name)}{lv}</div>'
            f'<audio controls preload="none" src="{e(rel(asset))}"></audio></div>')


def prompt_block(pid):
    it = PROMPTS.get(pid)
    if not it:
        return ""
    return (f'<p class="prompt">{e(it["sa3"]["prompt"])}</p>'
            f'<p class="neg">negative: {e(it["sa3"]["neg"])} · cfg {it["sa3"]["cfg"]} · '
            f'{it["seconds"]} s · {it["takes"]} takes</p>')


def card(cid, title, body, note_key, pid, extra=""):
    note = NOTES.get(note_key, "")
    return (f'<section class="card" id="{e(cid)}"><h3>{e(title)}{extra}</h3>'
            f'{f"<p class=desc>{e(note)}</p>" if note else ""}{prompt_block(pid)}'
            f'<div class="grid">{body}</div></section>')


def main():
    lv = S["levels_db"]
    parts = ["<h2 id='steps'>Footsteps</h2>",
             f"<p class='lead'>Each surface: single steps cut from Stable Audio 3 walking takes. "
             f"<b>Walk</b> plays random steps every {S['step_interval_s']} s at the proposed "
             f"footstep level ({lv['footsteps']} dB) over the rain bed ({lv['rain_bed']} dB), "
             f"never the same file twice in a row, each step at a random +-1.5 dB.</p>"]
    for surf, files in S["footsteps"].items():
        body = "".join(player(f) for f in files)
        btn = (f' <button data-walk="{e(surf)}">walk</button>'
               f' <span class="chip">{len(files)} steps</span>')
        parts.append(card(f"steps_{surf}", surf.replace("_", " "), body, f"steps_{surf}",
                          f"steps_{surf}", btn))
    parts.append("<h2 id='ui'>Clicks</h2>")
    parts.append(card("ui", "Walk and interact clicks",
                      player(S["click"]["walk"], "walk") + player(S["click"]["interact"], "interact"),
                      "ui", "ui_walk"))
    parts.append(f"<p class='prompt'>interact prompt: {e(PROMPTS['ui_interact']['sa3']['prompt'])}</p>")
    parts.append("<h2 id='objects'>Hotspots</h2>")
    for hid, files in S["hotspots"].items():
        parts.append(card(f"obj_{hid}", hid.replace("_", " "), "".join(player(f) for f in files),
                          f"obj_{hid}", f"obj_{hid}"))
    parts.append("<h2 id='doors'>Doors</h2>")
    for pid, d in S["portals"].items():
        parts.append(card(pid, pid.replace("_", " "),
                          player(d["open"], "open") + player(d["close"], "close"),
                          "doors", "door_open"))
    parts.append(f"<p class='prompt'>close prompt: {e(PROMPTS['door_close']['sa3']['prompt'])}</p>")
    rows = "".join(f"<tr><td>{e(k)}</td><td>{e(v)}</td><td>{e(NOTES.get('level_' + k, ''))}</td></tr>"
                   for k, v in lv.items())
    parts.append(f"<h2 id='levels'>Proposed levels (levels_db)</h2><table><tr><th>category</th>"
                 f"<th>dB</th><th>why</th></tr>{rows}</table>")
    rej = "".join(f"<li>{e(r)}</li>" for r in NOTES.get("rejected", []))
    parts.append(f"<h2 id='rejected'>Rejected takes</h2><ul>{rej}</ul>")

    walk = {s: [rel(f) for f in fs] for s, fs in S["footsteps"].items()}
    js = f"""
const WALK={json.dumps(walk)}, IV={S['step_interval_s']}, STEP_DB={lv['footsteps']}, RAIN_DB={lv['rain_bed']};
// HTMLAudioElement, so the page also works from file://
const vol = db => Math.min(1, Math.pow(10, db / 20));
let timer = null, rain = null;
function stop() {{ clearInterval(timer); timer = null; if (rain) {{ rain.pause(); rain = null; }}
  document.querySelectorAll('[data-walk]').forEach(b => b.textContent = 'walk'); }}
document.addEventListener('click', ev => {{
  const b = ev.target.closest('[data-walk]'); if (!b) return;
  const was = b.textContent === 'stop'; stop(); if (was) return;
  b.textContent = 'stop';
  rain = new Audio('{FINAL}/rain_bed_ref.wav'); rain.loop = true; rain.volume = vol(RAIN_DB); rain.play();
  const files = WALK[b.dataset.walk]; let last = -1;
  const step = () => {{ let i; do {{ i = Math.floor(Math.random() * files.length); }} while (i === last && files.length > 1);
    last = i; const a = new Audio(files[i]); a.volume = vol(STEP_DB + (Math.random() * 3 - 1.5)); a.play(); }};
  step(); timer = setInterval(step, IV * 1000);
}});
"""
    nav = "".join(f'<a href="#{a}">{t}</a>' for a, t in
                  [("steps", "footsteps"), ("ui", "clicks"), ("objects", "hotspots"),
                   ("doors", "doors"), ("levels", "levels"), ("rejected", "rejected")])
    css = (AUDIO / "scripts" / "build_index.py").read_text().split('CSS = """')[1].split('"""')[0]
    css += (".grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:4px 16px}"
            "button{font:inherit;font-size:13px;padding:1px 10px;border-radius:12px;border:1px solid var(--line);"
            "background:var(--chip);color:var(--fg);cursor:pointer}"
            "table{border-collapse:collapse;font-size:14px}td,th{border-bottom:1px solid var(--line);"
            "padding:4px 10px;text-align:left;vertical-align:top}li{margin:3px 0;font-size:14px}")
    page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Courtyard game sounds</title><style>{css}</style></head>
<body><main>
<h1>Courtyard game sounds</h1>
<p class="lead">Footsteps per surface, clicks, one sound per hotspot and the tower door, all from
Stable Audio 3 (local, MLX), as listed in <code>game/data/sounds.json</code>. The players play
the files at their normalized level, not the in-game level; the walk buttons use the proposed
in-game levels. Prompts are in <code>audio/prompts.json</code> under <code>game_sfx</code>.</p>
<nav>{nav}</nav>
{''.join(parts)}
</main><script>{js}</script></body></html>
"""
    (AUDIO / "game.html").write_text(page)
    print("wrote", AUDIO / "game.html")


if __name__ == "__main__":
    main()
