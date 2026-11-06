"""Fork one winning video: keep its structure (shots, cut timing, text rhythm), change one thing, swap the ending for our CTA.

Split, by screen time:
  ~80% copy   every shot is re-shot by the video model from the original frame as reference (same framing, action,
              light, cut length) with a new person/plate/kitchen, and the original's on-screen text kept almost word for word
  ~10% test   one experiment: a new hook line on shot 1 (logged, so the views decide if it stays)
  ~10% CTA    the last beat is our product, real app screen, in the creator's text style
We never reuse the creator's footage or face: the frames are only references.
"""
from __future__ import annotations

import base64
import io
import json
import urllib.request

from PIL import Image, ImageFilter

from . import gmi


def _data_url(url: str) -> str:
    """Oriane frames are webp on a CDN; send them inline as small JPEGs so any vision model can read them."""
    raw = urllib.request.urlopen(urllib.request.Request(url, headers={"user-agent": "fork-and-ship/0.1"}), timeout=30).read()
    im = Image.open(io.BytesIO(raw)).convert("RGB")
    im.thumbnail((512, 512))
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=80)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()

FORK_SYSTEM = """You fork a winning short video for another product. You get the original's timeline from a video-intelligence
API (on-screen text with timestamps, spoken words, length) and its frames as images, in order.
Return ONE JSON object:
{
 "shots": [ {"start": s, "end": s,
             "prompt": str /* re-shoot THIS frame: same framing, camera angle, action, light, colours; a different person
                              (or hands only), different plate and kitchen; vertical phone footage; no text in frame */,
             "on_screen_text": str /* the original's text at this time, kept ~80% word for word; adapt only words that
                                       would be false for us */ } ],
 "text_style": {"y": number /* 0-1, vertical centre of the creator's on-screen text */,
                "size": "small" | "medium" | "large"},
 "experiment": {"what": "hook", "original": str, "variant": str /* a sharper first line, <= 9 words, same tone */,
                "why": str},
 "cta": {"on_screen_text": str /* <= 10 words, in the creator's voice, names the product once, no hype */,
         "seconds": 2.5},
 "music_prompt": str /* instrumental bed in the spirit of the original's sound (title/author given), genre + mood + tempo */,
 "caption": str /* <= 140 chars, lowercase, close to the original's caption style */,
 "hashtags": [str] /* 3-5, no # */
}
Rules: 2 to 4 shots covering the original's first <= 12 seconds, cut where the picture changes between frames (OCR text may be noisy), each shot 1.5-5 s.
Each shot prompt must describe what its reference frame actually shows (subject, action, angle, props), so the
re-shoot matches it; only the person, exact plate and room change. Copy the structure, not the person. The product appears only in the CTA."""


def _segments(w: dict, max_s: float = 12.0) -> list[dict]:
    """Cut points where the on-screen text changes, from Oriane's per-frame text."""
    tl = [m for m in w.get("text_timeline", []) if m["t"] <= max_s]
    cuts, last = [], None
    for m in tl:
        if m["text"] != last:
            cuts.append(m)
            last = m["text"]
    return cuts[:8]


def plan_fork(w: dict, product: dict, frames: list[dict]) -> dict:
    """frames: [{"t": seconds, "url": ...}] from Oriane, first ~12 s of the original."""
    frame_urls = [f["url"] for f in frames]
    user_text = json.dumps({
        "product": product,
        "original": {k: w.get(k) for k in ("url", "views", "followers", "views_per_follower", "duration_s", "spoken_hook",
                                            "caption", "audio")},
        "text_changes": _segments(w),
        "frames_in_order": [{"i": i, "t": f["t"]} for i, f in enumerate(frames)],
    }, ensure_ascii=False)
    content = [{"type": "text", "text": user_text}] + [{"type": "image_url", "image_url": {"url": _data_url(u)}} for u in frame_urls[:6]]
    try:
        return gmi.chat_json(FORK_SYSTEM, content)
    except Exception as e:
        print(f"fork: vision call failed ({e}); planning from the timeline only")
        return gmi.chat_json(FORK_SYSTEM, user_text)  # model without vision: timeline only


def frame_at(w: dict, t: float) -> str | None:
    best = min(w.get("frames") or [], key=lambda f: abs(f["t"] - t), default=None)
    return best.get("url") if best else None


def frame_obj(w: dict, t: float) -> dict | None:
    return min(w.get("frames") or [], key=lambda f: abs(f["t"] - t), default=None)


def clean_ref(frame: dict) -> str:
    """The original frame with its on-screen text blurred out (Oriane's text boxes), as a data URL.

    Without this the video model copies the creator's caption into our shot and our text lands on top of theirs.
    """
    raw = urllib.request.urlopen(urllib.request.Request(frame["url"], headers={"user-agent": "fork-and-ship/0.1"}), timeout=30).read()
    im = Image.open(io.BytesIO(raw)).convert("RGB")
    W, H = im.size
    for x0, y0, x1, y1 in frame.get("text_boxes") or []:
        pad = 0.02
        box = (max(0, int((x0 - pad) * W)), max(0, int((y0 - pad) * H)), min(W, int((x1 + pad) * W)), min(H, int((y1 + pad) * H)))
        if box[2] > box[0] and box[3] > box[1]:
            im.paste(im.crop(box).filter(ImageFilter.GaussianBlur(18)), box)
    im.thumbnail((720, 1280))
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=85)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
