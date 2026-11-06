"""Oriane video intelligence: find videos that beat their account size, then read what they show, say and sound like."""
from __future__ import annotations

import json
import os
import urllib.request

BASE = "https://connect.oriane.xyz/rest"


def _post(path: str, body: dict, query: str = "") -> dict:
    key = os.environ["ORIANE_API_KEY"]
    req = urllib.request.Request(
        f"{BASE}{path}{query}",
        data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {key}", "content-type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.loads(r.read())


def search_videos(keywords: list[str], *, min_views: int = 50_000, after: str = "2026-05-01",
                  limit: int = 25, sort: str = "viewsRatePerFollowers") -> list[dict]:
    """TikTok videos whose spoken words, on-screen text or caption hit the niche.

    Sorted by views per follower by default: a small account with a huge video proves the format, not the fame.
    """
    fuzzy = {"includesExactly": {"values": keywords, "operator": "or"}}
    body = {
        "operator": "and",
        "filters": {
            "platform": {"includes": ["tiktok"]},
            "format": {"includes": ["video"]},
            "viewsCount": {"min": min_views},
            "publishedAt": {"after": after},
        },
        "queries": [
            {"name": "said", "operator": "or", "filters": {"transcript": fuzzy}},
            {"name": "shown", "operator": "or", "filters": {"onScreenText": fuzzy}},
            {"name": "captioned", "operator": "or", "filters": {"caption": fuzzy}},
        ],
    }
    # Nested queries combine with the top-level filters by the top operator; we want filters AND (said OR shown OR captioned).
    body = {"operator": "and", "filters": body["filters"],
            "queries": [{"operator": "or", "queries": body["queries"]}]}
    r = _post("/contents/search", body, f"?limit={limit}&projection=full&sort={sort}")
    return r["data"]["results"]


def _box(poly: list[dict]) -> list[float]:
    """Polygon (0-1 coords) to [x0, y0, x1, y1]."""
    xs, ys = [p.get("x", 0) for p in poly], [p.get("y", 0) for p in poly]
    return [min(xs), min(ys), max(xs), max(ys)]


def anatomy(c: dict) -> dict:
    """One video broken into the parts a remake needs: hook, text on screen over time, sound, pacing."""
    m = (c.get("media") or [{}])[0]
    chunks = m.get("transcriptChunks") or []
    frames = m.get("frames") or []
    dur = m.get("duration") or 0
    timeline = []
    for f in frames:
        texts = [t["text"].strip() for t in (f.get("onScreenTextRegions") or []) if t.get("text", "").strip()]
        if texts:
            timeline.append({"t": round(f.get("timestampSeconds") or 0, 1), "text": " / ".join(dict.fromkeys(texts))[:160]})
    followers = c.get("profileFollowersCount") or 0
    views = c.get("viewsCount") or 0
    return {
        "id": c.get("id"),
        "url": f"https://www.tiktok.com/@{c.get('profileHandle')}/video/{c.get('platformId')}",
        "handle": c.get("profileHandle"),
        "views": views,
        "followers": followers,
        "views_per_follower": round(views / followers, 1) if followers else None,
        "likes": c.get("likesCount"),
        "shares": c.get("sharesCount"),
        "published": (c.get("publishedAt") or "")[:10],
        "duration_s": dur,
        "caption": (c.get("caption") or "")[:300],
        "hashtags": c.get("hashtags") or [],
        "audio": {"title": c.get("audioTitle"), "author": c.get("audioAuthor"), "type": c.get("audioType")},
        "spoken_hook": " ".join(ch["text"] for ch in chunks if (ch.get("startSeconds") or 0) < 3).strip()[:300],
        "transcript": (m.get("transcript") or "")[:1500],
        "words_per_second": round(len((m.get("transcript") or "").split()) / dur, 2) if dur else None,
        "first_text_on_screen": timeline[0] if timeline else None,
        "text_timeline": timeline[:25],
        "frames_sampled": len(frames),
        "thumbnail": c.get("thumbnailMediaUrl") or (frames[0].get("url") if frames else None),
        "frame_urls": [f.get("url") for f in frames[:: max(1, len(frames) // 6)]][:6],
        "frames": [{"t": round(f.get("timestampSeconds") or 0, 2), "url": f.get("url"),
                    "text_boxes": [_box(r.get("polygon") or []) for r in (f.get("onScreenTextRegions") or []) if r.get("polygon")]}
                   for f in frames][:80],
        "matched": c.get("matchedQueries") or [],
    }
