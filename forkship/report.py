"""One static page for the demo: what Oriane saw, the original next to our fork shot by shot, the 4 hook variants."""
from __future__ import annotations

import html
import json
import os
import subprocess

DATA = os.environ.get("FORKSHIP_DATA", "data")
E = html.escape


def _load(name, default):
    p = os.path.join(DATA, name)
    return json.load(open(p)) if os.path.exists(p) else default


def _fmt(n):
    if n is None:
        return "–"
    return f"{n / 1e6:.1f}M" if n >= 1e6 else f"{n / 1e3:.0f}K" if n >= 1e3 else str(n)


def _thumb(video: str, t: float, out: str) -> str:
    """A frame of our video at t seconds, for the side-by-side grid."""
    if os.path.exists(video):
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", f"{t:.2f}", "-i", video, "-frames:v", "1",
                        "-vf", "scale=360:-1", os.path.join(DATA, out)], check=False)
    return out


def _timeline(w) -> str:
    dur = max(w.get("duration_s") or 1, 1)
    marks = "".join(f'<i style="left:{min(99, 100 * m["t"] / dur):.1f}%"></i>' for m in w.get("text_timeline", []))
    return f'<div class="tl"><b style="width:{100 * min(3, dur) / dur:.1f}%"></b>{marks}</div>'


CSS = """
:root{--bg:#09090b;--card:#141418;--line:#26262c;--mut:#8b8b95;--txt:#ececf1;--acc:#a78bfa;--say:#6ee7a8;--show:#e8f07a;--snd:#93a7ff}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--txt);font:15px/1.5 Inter,-apple-system,system-ui,sans-serif}
.wrap{max-width:1240px;margin:0 auto;padding:48px 32px 80px}
.eyebrow{font:600 12px/1 ui-monospace,Menlo,monospace;letter-spacing:.14em;color:var(--acc);text-transform:uppercase}
h1{font-size:56px;line-height:1;letter-spacing:-.03em;margin:14px 0 12px}
h2{font-size:28px;letter-spacing:-.02em;margin:0 0 6px}
.lead{color:var(--mut);font-size:18px;max-width:760px;margin:0}
.chips{display:flex;gap:8px;margin-top:22px;flex-wrap:wrap}.chip{border:1px solid var(--line);border-radius:999px;padding:6px 14px;color:#c9c9d1;font-size:13px}
.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:34px 0 8px}
.stat{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:18px 20px}
.stat b{display:block;font-size:30px;letter-spacing:-.02em}.stat span{color:var(--mut);font-size:13px}
section{margin-top:64px}.sub{color:var(--mut);margin:0 0 22px}
.steps{display:grid;grid-template-columns:repeat(5,1fr);gap:10px}
.step{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:16px}
.step i{font:600 11px ui-monospace,Menlo,monospace;color:var(--acc);font-style:normal}.step p{margin:6px 0 0;font-size:14px}
.step small{color:var(--mut)}
.split{display:flex;height:34px;border-radius:10px;overflow:hidden;margin:18px 0 8px;font:600 12px/34px Inter,sans-serif}
.split div{padding:0 12px;white-space:nowrap;color:#0a0a0c}
.legend{display:flex;gap:22px;color:var(--mut);font-size:13px}
.pairs{display:grid;grid-auto-flow:column;grid-auto-columns:1fr;gap:12px}
.pair{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:10px}
.pair img{width:100%;aspect-ratio:9/16;object-fit:cover;border-radius:10px;display:block;background:#1d1d22}
.pair .lab{font:600 11px ui-monospace,Menlo,monospace;color:var(--mut);margin:8px 2px 6px;letter-spacing:.08em}
.pair .cap{font-size:12px;color:#c9c9d1;margin:8px 2px 2px}
.vars{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}
.var{background:var(--card);border:1px solid var(--line);border-radius:18px;padding:12px}
.var video{width:100%;aspect-ratio:9/16;border-radius:12px;background:#000;display:block}
.tag{display:inline-block;font:700 11px ui-monospace,Menlo,monospace;border-radius:6px;padding:3px 7px;margin:12px 0 6px;color:#0a0a0c;background:var(--show)}
.tag.ctl{background:#d4d4d8}.var h3{font-size:16px;margin:0 0 4px;letter-spacing:-.01em}.var p{margin:0;color:var(--mut);font-size:13px}
.grid{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}
.card{background:var(--card);border:1px solid var(--line);border-radius:16px;overflow:hidden;color:var(--txt);text-decoration:none}
.card img{width:100%;aspect-ratio:4/5;object-fit:cover;display:block;background:#1d1d22}
.card .in{padding:12px 14px 14px}.card .n{font-size:13px;color:var(--mut)}.card .n b{color:var(--txt);font-size:15px}
.x{float:right;background:#2a2340;color:var(--acc);border-radius:6px;padding:1px 7px;font-weight:700;font-size:12px}
.tl{position:relative;height:6px;margin:12px 0 10px;background:#25252b;border-radius:4px}
.tl b{position:absolute;inset:0 auto 0 0;background:var(--say);border-radius:4px;opacity:.8}.tl i{position:absolute;top:-3px;width:2px;height:12px;background:var(--show)}
.row{font-size:12.5px;color:#c9c9d1;margin-top:5px;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.k{font:700 10px ui-monospace,Menlo,monospace;border-radius:4px;padding:1px 5px;margin-right:6px;color:#0a0a0c}
.say{background:var(--say)}.show{background:var(--show)}.snd{background:var(--snd)}
a.src{color:var(--acc)}footer{margin-top:72px;color:var(--mut);font-size:13px;border-top:1px solid var(--line);padding-top:20px}
"""


def build() -> str:
    winners = _load("research.json", [])
    plan = _load("plan.json", {})
    cfg = json.load(open(os.environ.get("FORKSHIP_CONFIG", "product.json")))
    src = plan.get("source") or {}
    shots = (plan.get("remake") or {}).get("shots", [])
    variants = plan.get("variants") or ([{"label": "A", "hook": (plan.get("remake") or {}).get("hook_text", ""), "why": "", "video": plan["video"]}]
                                        if plan.get("video") else [])
    split = plan.get("split") or {}
    cta = plan.get("cta") or {}

    # Original vs fork, shot by shot (fork frames from variant B so the test hook shows on shot 1 next to the control's text).
    ours = (variants[1] if len(variants) > 1 else variants[0])["video"] if variants else ""
    pairs, t = [], 0.0
    for i, s in enumerate(shots):
        mid = t + s["seconds"] / 2
        img = _thumb(ours, mid, f"cmp_{i}.jpg")
        pairs.append(f"""<div class="pair"><div class="lab">SHOT {i + 1} · {s['seconds']}s</div>
<img src="{s.get('ref')}" title="original"><div class="cap">original</div>
<img src="{img}" style="margin-top:8px"><div class="cap">ours · “{E(s.get('on_screen_text', ''))}”</div></div>""")
        t += s["seconds"]
    if variants:
        img = _thumb(variants[0]["video"], t + float(cta.get("seconds", 1.2)) / 2, "cmp_cta.jpg")
        pairs.append(f"""<div class="pair"><div class="lab">CTA · {cta.get('seconds')}s</div>
<div style="aspect-ratio:9/16;border-radius:10px;border:1px dashed var(--line);display:grid;place-items:center;color:var(--mut);font-size:12px">their ending</div>
<div class="cap">original</div><img src="{img}" style="margin-top:8px"><div class="cap">ours · “{E(cta.get('on_screen_text', ''))}”</div></div>""")

    copy_s, cta_s = float(split.get("copy_s") or sum(s["seconds"] for s in shots) or 1), float(cta.get("seconds") or 1.2)
    hook_s = min(1.0, shots[0]["seconds"]) if shots else 0.5
    total = copy_s + cta_s
    bar = (f'<div class="split"><div style="flex:{copy_s - hook_s};background:var(--say)">copy · {100 * (copy_s - hook_s) / total:.0f}%</div>'
           f'<div style="flex:{hook_s};background:var(--show)">test {100 * hook_s / total:.0f}%</div>'
           f'<div style="flex:{cta_s};background:var(--acc)">CTA {100 * cta_s / total:.0f}%</div></div>')

    vars_html = "".join(f"""<div class="var"><video src="{os.path.basename(v['video'])}" controls playsinline loop preload="metadata"></video>
<span class="tag {'ctl' if i == 0 else ''}">{v['label']} · {'CONTROL' if i == 0 else 'TEST'}</span><h3>“{E(v['hook'])}”</h3><p>{E(v.get('why', ''))}</p></div>"""
                        for i, v in enumerate(variants))

    cards = []
    for w in winners[:8]:
        first = w.get("first_text_on_screen") or {}
        cards.append(f"""<a class="card" href="{w['url']}" target="_blank"><img src="{w.get('thumbnail') or ''}" loading="lazy">
<div class="in"><div class="n"><b>{_fmt(w['views'])}</b> views · {_fmt(w['followers'])} followers <span class="x">{w.get('views_per_follower') or '–'}x</span></div>
{_timeline(w)}
<div class="row"><span class="k say">SAY</span>{E(w.get('spoken_hook') or 'no voice')}</div>
<div class="row"><span class="k show">SHOW {first.get('t', '–')}s</span>{E(first.get('text', 'no text'))}</div>
<div class="row"><span class="k snd">SOUND</span>{E((w.get('audio') or {}).get('title') or '–')} · {w.get('duration_s')}s</div></div></a>""")

    page = f"""<!doctype html><html><head><meta charset="utf-8"><title>Fork & Ship</title>
<meta name="viewport" content="width=device-width,initial-scale=1"><style>{CSS}</style></head><body><div class="wrap">
<div class="eyebrow">Hack the Feed · Oriane × GMI Cloud × Outnumber</div>
<h1>Fork &amp; Ship</h1>
<p class="lead">Find the video that is winning in your niche this week. Re-shoot it shot by shot for your product, test one hook, post it. The views pick the next one.</p>
<div class="chips"><span class="chip">Oriane video intelligence</span><span class="chip">GMI · Gemini 3.8 Flash</span><span class="chip">GMI · Seedance 2.0</span><span class="chip">GMI · MiniMax Music</span><span class="chip">Outnumber API</span></div>
<div class="stats">
 <div class="stat"><b>{len(winners)}</b><span>niche videos read by Oriane</span></div>
 <div class="stat"><b>{src.get('views_per_follower', '–')}x</b><span>views per follower on the one we forked</span></div>
 <div class="stat"><b>{len(shots)} shots</b><span>re-shot from the original's frames</span></div>
 <div class="stat"><b>{len(variants)} hooks</b><span>same footage, so views compare fairly</span></div>
</div>

<section><div class="eyebrow">How it works</div><h2>One command, five steps</h2><p class="sub">python -m forkship.agent fork</p>
<div class="steps">
 <div class="step"><i>01 · ORIANE</i><p>Find winners by views per follower</p><small>small accounts, huge views = the format works</small></div>
 <div class="step"><i>02 · ORIANE</i><p>Read each second</p><small>spoken words, on-screen text + boxes, sound, cuts</small></div>
 <div class="step"><i>03 · GMI LLM</i><p>Plan the fork from the frames</p><small>shot list, text, 3 hook bets, CTA, music brief</small></div>
 <div class="step"><i>04 · GMI VIDEO</i><p>Re-shoot every shot</p><small>original frame as reference, its text blurred out</small></div>
 <div class="step"><i>05 · OUTNUMBER</i><p>Post A/B/C/D, read views</p><small>the winning hook becomes the next control</small></div>
</div></section>

<section><div class="eyebrow">The fork</div><h2>Original vs ours, shot by shot</h2>
<p class="sub">Source: <a class="src" href="{src.get('url', '#')}" target="_blank">@{E(src.get('handle', ''))}</a> · {_fmt(src.get('views'))} views on {_fmt(src.get('followers'))} followers · {src.get('duration_s')}s. Same framing, action and cut length; new hands, plate and kitchen; their text never copied from pixels.</p>
{bar}
<div class="legend"><span>copy: shots, timing, on-screen text</span><span>test: the hook line</span><span>CTA: real app screen</span></div>
<div class="pairs" style="margin-top:18px">{''.join(pairs)}</div></section>

<section><div class="eyebrow">The test</div><h2>{len(variants)} videos, one variable</h2>
<p class="sub">Everything is identical except the first line. A is the original hook. Each goes to a different account; the views decide.</p>
<div class="vars">{vars_html}</div></section>

<section><div class="eyebrow">What Oriane saw</div><h2>Winners in “{E(cfg['niche_phrases'][0])}”</h2>
<p class="sub">Green bar = first 3 seconds of speech. Yellow ticks = text appearing on screen. Ranked by views per follower.</p>
<div class="grid">{''.join(cards)}</div></section>

<footer>github.com/arrrtem22/fork-and-ship · built in 3 hours at Amplitude HQ, Nov 6 2026</footer>
</div></body></html>"""
    out = os.path.join(DATA, "index.html")
    open(out, "w").write(page)
    return out


if __name__ == "__main__":
    print(build())
