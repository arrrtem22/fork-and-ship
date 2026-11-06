"""One static page for the demo: what Oriane saw in the winners, the format we picked, the video we made, what it did."""
from __future__ import annotations

import html
import json
import os

DATA = os.environ.get("FORKSHIP_DATA", "data")


def _load(name, default):
    p = os.path.join(DATA, name)
    return json.load(open(p)) if os.path.exists(p) else default


def _fmt(n):
    if n is None:
        return "–"
    return f"{n / 1e6:.1f}M" if n >= 1e6 else f"{n / 1e3:.0f}K" if n >= 1e3 else str(n)


def _timeline(w) -> str:
    """Seconds bar: spoken hook in green, on-screen text marks in yellow. The 'show / say' of each winner at a glance."""
    dur = max(w.get("duration_s") or 1, 1)
    marks = "".join(
        f'<i class="t" style="left:{min(99, 100 * m["t"] / dur):.1f}%" title="{html.escape(m["text"])} @ {m["t"]}s"></i>'
        for m in w.get("text_timeline", []))
    hook_w = 100 * min(3, dur) / dur
    return f'<div class="bar"><b class="hook" style="width:{hook_w:.1f}%"></b>{marks}</div>'


def build() -> str:
    winners = _load("research.json", [])
    plan = _load("plan.json", {})
    shipped = _load("shipped.json", [])
    results = _load("results.json", [])
    cards = []
    for w in winners[:12]:
        first = (w.get("first_text_on_screen") or {})
        cards.append(f"""
<a class="card" href="{w['url']}" target="_blank">
  <img src="{w.get('thumbnail') or ''}" loading="lazy">
  <div class="stat"><b>{_fmt(w['views'])}</b> views · {_fmt(w['followers'])} followers · <b>{w.get('views_per_follower') or '–'}x</b></div>
  {_timeline(w)}
  <div class="row"><span class="k say">says 0-3s</span>{html.escape(w.get('spoken_hook') or '(no voice)')[:110]}</div>
  <div class="row"><span class="k show">shows @{first.get('t', '–')}s</span>{html.escape(first.get('text', '(no text)'))[:90]}</div>
  <div class="row"><span class="k snd">sound</span>{html.escape((w.get('audio') or {}).get('title') or '–')[:50]} · {w.get('duration_s')}s · {w.get('words_per_second') or 0} w/s</div>
</a>""")
    formats = "".join(
        f"<li><b>{html.escape(f['name'])}</b> ({len(f.get('videos', []))} videos): {html.escape(f.get('pattern', ''))}"
        f"<br><small>{html.escape(f.get('evidence', ''))}</small></li>" for f in plan.get("formats", []))
    shots = "".join(
        f"<li><b>{s.get('seconds')}s</b> “{html.escape(s.get('on_screen_text', ''))}”<br><small>{html.escape(s.get('prompt', ''))}</small></li>"
        for s in (plan.get("remake") or {}).get("shots", []))
    video = os.path.basename(plan.get("video", "")) if plan.get("video") else ""
    src = plan.get("source") or {}
    refs = "".join(f'<figure><img src="{s.get("ref")}"><figcaption>{s.get("seconds")}s · “{html.escape(s.get("on_screen_text", ""))}”</figcaption></figure>'
                   for s in (plan.get("remake") or {}).get("shots", []) if s.get("ref"))
    exp = plan.get("experiment") or {}
    cta = plan.get("cta") or {}
    split = (f"""<div class="split"><div><h3>Original · <a href="{src.get('url')}" target="_blank">@{html.escape(src.get('handle', ''))}</a>
 · {_fmt(src.get('views'))} views · {src.get('views_per_follower')}x followers</h3><div class="refs">{refs}</div>
 <p><span class="k say">80% copy</span>each shot re-shot from the original frame: same framing, action, cut length, text. New person, plate, kitchen.</p>
 <p><span class="k show">10% test</span>hook “{html.escape(exp.get('original', ''))}” → <b>“{html.escape(exp.get('variant', ''))}”</b> <small>{html.escape(exp.get('why', ''))}</small></p>
 <p><span class="k snd">10% CTA</span>{html.escape(cta.get('on_screen_text', ''))} <small>(real app screen)</small></p></div></div>""" if src else "")
    res_rows = "".join(
        f"<tr><td>{html.escape(r['format'])}</td><td>{html.escape(r['hook'])}</td><td>{r.get('status')}</td><td><b>{_fmt(r.get('views'))}</b></td></tr>"
        for r in results) or "".join(
        f"<tr><td>{html.escape(s['format'])}</td><td>{html.escape(s['hook'])}</td><td>queued</td><td>–</td></tr>" for s in shipped)
    page = f"""<!doctype html><html><head><meta charset="utf-8"><title>Fork & Ship</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
body{{background:#0b0b0d;color:#eee;font:15px/1.45 -apple-system,Inter,sans-serif;margin:0;padding:32px}}
h1{{font-size:34px;margin:0}} h2{{margin:36px 0 12px;font-size:20px;color:#e6f08a}} small{{color:#999}}
.sub{{color:#aaa;margin:6px 0 0}} .steps{{display:flex;gap:10px;margin:18px 0;flex-wrap:wrap}}
.steps span{{border:1px solid #333;border-radius:20px;padding:6px 14px;color:#ccc}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:14px}}
.card{{background:#16161a;border-radius:14px;overflow:hidden;color:#ddd;text-decoration:none;padding-bottom:10px}}
.card img{{width:100%;height:300px;object-fit:cover;background:#222}}
.stat,.row{{padding:4px 12px;font-size:13px}} .k{{display:inline-block;font-size:11px;border-radius:6px;padding:1px 6px;margin-right:6px;color:#000}}
.say{{background:#7ee0a0}} .show{{background:#e6f08a}} .snd{{background:#a9b8ff}}
.bar{{position:relative;height:10px;margin:8px 12px;background:#2a2a30;border-radius:5px}}
.bar .hook{{position:absolute;left:0;top:0;bottom:0;background:#7ee0a0;border-radius:5px;opacity:.7}}
.bar .t{{position:absolute;top:-2px;width:3px;height:14px;background:#e6f08a}}
.two{{display:grid;grid-template-columns:360px 1fr;gap:28px;align-items:start}}
video{{width:360px;border-radius:16px;background:#000}} li{{margin:8px 0}}
.refs{{display:flex;gap:8px;flex-wrap:wrap}} figure{{margin:0;width:150px}} figure img{{width:150px;height:266px;object-fit:cover;border-radius:10px}}
figcaption{{font-size:12px;color:#aaa}} .split{{margin-bottom:20px}} h3{{font-size:15px;font-weight:600}} a{{color:#e6f08a}}
table{{border-collapse:collapse;width:100%}} td,th{{border-bottom:1px solid #2a2a30;padding:8px;text-align:left}}
</style></head><body>
<h1>Fork & Ship</h1>
<p class="sub">Find the video format that is winning this week. Remake it for your product. Post it. Learn from the views. Repeat.</p>
<div class="steps"><span>1 · Oriane reads the winners</span><span>2 · GMI LLM names the formats</span><span>3 · GMI video model shoots the remake</span><span>4 · Outnumber posts it</span><span>5 · views feed the next round</span></div>
<h2>1 · Winners in “{html.escape(', '.join(json.load(open(os.environ.get('FORKSHIP_CONFIG', 'product.json')))['niche_phrases'][:3]))}”, ranked by views per follower</h2>
<p class="sub">Green = what they say in the first 3 s. Yellow ticks = text on screen over time. Small accounts with huge views prove the format, not the fame.</p>
<div class="grid">{''.join(cards)}</div>
<h2>2 · Formats found</h2><ul>{formats or '<li>run plan</li>'}</ul>
<p><b>Picked:</b> {html.escape(plan.get('chosen_format', '–'))}. {html.escape(plan.get('why', ''))}</p>
<h2>3 · Our fork</h2>{split}
<div class="two"><div>{f'<video src="{video}" controls playsinline loop></video>' if video else 'run render'}</div>
<div><p><b>Hook (0-2s):</b> {html.escape((plan.get('remake') or {}).get('hook_text', ''))}</p><ol>{shots}</ol>
<p><b>Caption:</b> {html.escape((plan.get('remake') or {}).get('caption', ''))} {' '.join('#' + t for t in (plan.get('remake') or {}).get('hashtags', []))}</p></div></div>
<h2>4 · Shipped through Outnumber, 5 · what it did</h2>
<table><tr><th>Format</th><th>Hook</th><th>Status</th><th>Views</th></tr>{res_rows or '<tr><td colspan=4>nothing shipped yet</td></tr>'}</table>
</body></html>"""
    out = os.path.join(DATA, "index.html")
    open(out, "w").write(page)
    return out


if __name__ == "__main__":
    print(build())
