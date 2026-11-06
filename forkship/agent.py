"""Fork & Ship: find a video format that is winning right now, remake it for your product, post it, learn from the views.

    python -m forkship.agent research   # Oriane: winners in the niche, broken into hook / text / sound / pacing
    python -m forkship.agent plan       # GMI LLM: name the formats, pick one, write the remake shot by shot
    python -m forkship.agent render     # GMI video model + ffmpeg: one 9:16 mp4
    python -m forkship.agent ship       # Outnumber API: upload + queue on a TikTok account
    python -m forkship.agent learn      # Outnumber API: views of what we posted, fed into the next plan
    python -m forkship.agent loop       # all of the above, once
"""
from __future__ import annotations

import glob
import json
import os
import sys
import time

import math
import urllib.request

from . import fork as forker
from . import gmi, oriane, outnumber, render

DATA = os.environ.get("FORKSHIP_DATA", "data")
CONFIG = json.load(open(os.environ.get("FORKSHIP_CONFIG", "product.json")))


def _save(name: str, obj) -> None:
    os.makedirs(DATA, exist_ok=True)
    json.dump(obj, open(os.path.join(DATA, name), "w"), indent=1, ensure_ascii=False)


def _load(name: str, default=None):
    p = os.path.join(DATA, name)
    return json.load(open(p)) if os.path.exists(p) else default


def research() -> list[dict]:
    found = oriane.search_videos(CONFIG["niche_phrases"], min_views=CONFIG.get("min_views", 30_000),
                                 after=CONFIG.get("since", "2026-05-01"), limit=CONFIG.get("research_limit", 30))
    winners = [oriane.anatomy(c) for c in found]
    _save("research.json", winners)
    print(f"oriane: {len(winners)} winners")
    return winners


PLAN_SYSTEM = """You are a short-form video strategist. You get TikTok videos that beat their account size in one niche,
already broken down by a video-intelligence API: the spoken hook (first 3 s), on-screen text with timestamps,
audio track, duration, words per second, views per follower. You also get past results of our own remakes.

Return ONE JSON object:
{
 "formats": [ {"name": str, "videos": [video ids], "pattern": str,
               "evidence": str  /* cite numbers: hook second, text timing, length, wps, audio, views per follower */ } ],
 "chosen_format": str,
 "why": str  /* one sentence, cite the data and past results */,
 "remake": {
   "hook_text": str  /* first on-screen text, <= 9 words, shown 0-2 s */,
   "shots": [ {"seconds": 3-5, "prompt": str /* text-to-video prompt, vertical phone footage, NO text in frame */,
               "on_screen_text": str /* <= 12 words */} ]  /* 3 to 4 shots, total 10-16 s */,
   "caption": str  /* <= 140 chars, lowercase, no emoji spam */,
   "hashtags": [str]  /* 3-5, without # */
 }
}
Rules: copy the winning STRUCTURE (hook timing, text rhythm, length, shot types), never the creator's words or face.
The product appears naturally in one shot as a phone screen or mention, not as an ad. Prompts must be filmable by a
video model: one subject, one action, phone-camera look, warm natural light."""


def plan() -> dict:
    winners = _load("research.json") or research()
    slim = [{k: w[k] for k in ("id", "views", "followers", "views_per_follower", "duration_s", "spoken_hook",
                                "first_text_on_screen", "text_timeline", "words_per_second", "audio", "caption")}
            for w in winners[:15]]
    for s in slim:
        s["text_timeline"] = s["text_timeline"][:10]
    user = json.dumps({"product": CONFIG["product"], "winners": slim, "our_past_results": _load("results.json", [])},
                      ensure_ascii=False)
    p = gmi.chat_json(PLAN_SYSTEM, user)
    tags = [t.lstrip("#") for t in p["remake"].get("hashtags", [])]
    for t in CONFIG.get("always_hashtags", []):
        if t not in tags:
            tags.append(t)
    p["remake"]["hashtags"] = tags[:5]
    p["created_at"] = int(time.time())
    _save("plan.json", p)
    print(f"plan: {p['chosen_format']} | {p['remake']['hook_text']}")
    return p


def _generate(prompt: str, seconds: int) -> str:
    # Video models garble app screens: a shot of the product uses a real screenshot-in-hand photo instead.
    name = CONFIG["product"]["name"].lower()
    real = sorted(glob.glob(CONFIG.get("product_stills", "assets/product_*.jpg")))
    if name in prompt.lower() and real:
        return real[hash(prompt) % len(real)]
    if os.environ.get("GMI_API_KEY") and not os.environ.get("FORKSHIP_OFFLINE"):
        return gmi.wait_video(gmi.start_video(prompt, seconds=min(max(seconds, 5), 10)))
    stills = sorted(glob.glob(CONFIG.get("offline_stills", "assets/*.jpg")))
    return stills[hash(prompt) % len(stills)]


def render_video() -> str:
    p = _load("plan.json") or plan()
    shots = [dict(s) for s in p["remake"]["shots"]]
    shots[0]["on_screen_text"] = p["remake"]["hook_text"]
    work = os.path.join(DATA, f"render_{p['created_at']}")
    clips = render.render_shots(shots, work, _generate)
    if CONFIG.get("end_card"):
        clips.append(render.shot_clip(CONFIG["end_card"], "", 2.0, os.path.join(work, "end.mp4"), work))
    out = render.concat(clips, os.path.join(DATA, f"video_{p['created_at']}.mp4"))
    p["video"] = out
    _save("plan.json", p)
    print(f"render: {out}")
    return out


def pick_winner(winners: list[dict]) -> dict:
    """Most views per follower among videos with a forkable structure: text changes on screen, under 40 s."""
    if CONFIG.get("fork_id"):
        return next(w for w in winners if w["id"] == CONFIG["fork_id"])
    ok = [w for w in winners if w.get("frames") and len(forker._segments(w)) >= 2 and (w.get("duration_s") or 99) <= 40]
    return max(ok, key=lambda w: w.get("views_per_follower") or 0)


def fork() -> str:
    """Re-shoot a winner shot by shot (80%), test one hook (10%), end on our product (10%)."""
    winners = _load("research.json") or research()
    w = pick_winner(winners)
    early = [fr for fr in w["frames"] if fr["t"] <= 12]
    refs = early[:: max(1, math.ceil(len(early) / 6))][:6]
    f = forker.plan_fork(w, CONFIG["product"], refs)
    shots = f["shots"][:4]
    created = int(time.time())
    work = os.path.join(DATA, f"fork_{created}")
    gen_shots = []
    for i, s in enumerate(shots):
        seg = max(1.5, float(s["end"]) - float(s["start"]))
        text = f["experiment"]["variant"] if i == 0 and f.get("experiment") else s.get("on_screen_text", "")
        ts = f.get("text_style") or {}
        gen_shots.append({"prompt": s["prompt"], "seconds": seg, "on_screen_text": text,
                          "text_y": float(ts.get("y", 0.4)), "text_size": {"small": 50, "medium": 62, "large": 76}.get(ts.get("size"), 62),
                          "ref": forker.frame_at(w, float(s["start"]) + min(0.5, seg / 2)),
                          "ref_clean": forker.clean_ref(forker.frame_obj(w, float(s["start"]) + min(0.5, seg / 2)))})

    def generate(prompt, seconds, ref=None):
        if os.environ.get("FORKSHIP_OFFLINE") or not os.environ.get("GMI_API_KEY"):
            return _generate(prompt, seconds)
        rid = gmi.start_video(prompt + ". No text, captions or stickers in frame.", seconds=max(4, math.ceil(seconds)), reference_images=[ref] if ref else None)
        return gmi.wait_video(rid)

    live = os.environ.get("GMI_API_KEY") and not os.environ.get("FORKSHIP_OFFLINE")
    music_id = gmi.start_music(f.get("music_prompt") or "upbeat lofi cooking beat") if live else None
    clips = render.render_shots(gen_shots, work, lambda p, sec, _m={s["prompt"]: s["ref_clean"] for s in gen_shots}: generate(p, sec, _m.get(p)))
    cta = f.get("cta") or {"on_screen_text": CONFIG["product"]["name"], "seconds": 2.5}
    stills = sorted(glob.glob(CONFIG.get("product_stills", "assets/product_*.jpg")))
    clips.append(render.shot_clip(stills[0], cta["on_screen_text"], float(cta.get("seconds", 2.5)), os.path.join(work, "cta.mp4"), work,
                                  y_frac=gen_shots[0]["text_y"], size=gen_shots[0]["text_size"]))
    out = render.concat(clips, os.path.join(DATA, f"fork_{created}_silent.mp4"))
    if music_id:
        total = sum(s["seconds"] for s in gen_shots) + float(cta.get("seconds", 2.5))
        mp3 = os.path.join(work, "music.mp3")
        urllib.request.urlretrieve(gmi.wait_audio(music_id), mp3)
        out = render.add_music(out, mp3, os.path.join(DATA, f"fork_{created}.mp4"), total)
    p = {"created_at": created, "chosen_format": f"fork of @{w['handle']} ({w['views'] // 1000}K views, {w['views_per_follower']}x followers)",
         "why": f"{w['url']}: highest views per follower with a clear shot/text structure.",
         "source": {k: w[k] for k in ("url", "handle", "views", "followers", "views_per_follower", "duration_s")},
         "experiment": f.get("experiment"), "cta": cta, "music_prompt": f.get("music_prompt"),
         "formats": [], "remake": {"hook_text": gen_shots[0]["on_screen_text"],
                                   "shots": [{"seconds": round(s["seconds"], 1), "prompt": s["prompt"], "on_screen_text": s["on_screen_text"],
                                              "ref": s["ref"]} for s in gen_shots],
                                   "caption": f.get("caption", ""), "hashtags": ([t.lstrip("#") for t in f.get("hashtags", [])] + CONFIG.get("always_hashtags", []))[:5]},
         "video": out}
    _save("plan.json", p)
    print(f"fork: {out} from {w['url']}")
    return out


def music() -> str:
    """Add a GMI music bed to the current plan's video (for videos rendered before music existed)."""
    p = _load("plan.json")
    prompt = p.get("music_prompt") or "upbeat lofi hip hop cooking beat, warm and cozy, 90 bpm"
    total = sum(s["seconds"] for s in p["remake"]["shots"]) + float((p.get("cta") or {}).get("seconds", 2.5))
    mp3 = os.path.join(DATA, f"music_{p['created_at']}.mp3")
    urllib.request.urlretrieve(gmi.wait_audio(gmi.start_music(prompt)), mp3)
    out = render.add_music(p["video"], mp3, p["video"].replace(".mp4", "_music.mp4"), total)
    p["video"], p["music_prompt"] = out, prompt
    _save("plan.json", p)
    print(f"music: {out}")
    return out


def ship() -> dict:
    p = _load("plan.json")
    acc = os.environ.get("OUTNUMBER_ACCOUNT_ID") or outnumber.accounts()[0]["id"]
    media = outnumber.upload(p["video"])
    post = outnumber.queue_video(acc, media, p["remake"]["caption"], p["remake"]["hashtags"])
    shipped = _load("shipped.json", [])
    shipped.append({"post_id": post.get("id"), "account_id": acc, "format": p["chosen_format"],
                    "hook": p["remake"]["hook_text"], "video": p["video"], "queued_at": int(time.time())})
    _save("shipped.json", shipped)
    print(f"ship: queued post {post.get('id')} on account {acc}")
    return post


def learn() -> list[dict]:
    shipped = {s["post_id"]: s for s in _load("shipped.json", [])}
    rows = []
    for post in outnumber.posts():
        s = shipped.get(post.get("id"))
        if s:
            rows.append({"format": s["format"], "hook": s["hook"], "status": post.get("status"),
                         "views": (post.get("stats") or {}).get("views"), "posted_url": post.get("posted_url")})
    _save("results.json", rows)
    print(f"learn: {len(rows)} of our posts read back")
    return rows


def main() -> None:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "loop"
    steps = {"research": research, "plan": plan, "render": render_video, "fork": fork, "music": music, "ship": ship, "learn": learn}
    if cmd == "loop":
        if os.environ.get("OUTNUMBER_API_KEY"):
            learn()
        research(), plan(), render_video()
        if os.environ.get("OUTNUMBER_API_KEY"):
            ship()
    else:
        steps[cmd]()


if __name__ == "__main__":
    main()
