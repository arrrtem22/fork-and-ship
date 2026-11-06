"""Outnumber public API: upload the video, queue it on a TikTok account, read its views back."""
from __future__ import annotations

import json
import os
import urllib.request

BASE = os.environ.get("OUTNUMBER_API_URL", "https://www.useoutnumber.com/api/v1")


def _req(method: str, path: str, body: dict | None = None) -> dict:
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Authorization": f"Bearer {os.environ['OUTNUMBER_API_KEY']}", "content-type": "application/json"},
        method=method,
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def accounts() -> list[dict]:
    return _req("GET", "/accounts")["data"]


def upload(path: str) -> str:
    """Signed upload of one mp4; returns the storage path for POST /posts."""
    size = os.path.getsize(path)
    up = _req("POST", "/uploads", {"file_name": os.path.basename(path), "content_type": "video/mp4", "size": size})["data"]
    with open(path, "rb") as f:
        put = urllib.request.Request(up["upload_url"], data=f.read(), method="PUT",
                                     headers={"content-type": "video/mp4", "x-upsert": "true"})
        urllib.request.urlopen(put, timeout=300).read()
    return up["path"]


def queue_video(account_id: str, media_path: str, caption: str, hashtags: list[str]) -> dict:
    return _req("POST", "/posts", {"account_id": account_id, "kind": "video", "media": [media_path],
                                    "caption": caption, "hashtags": hashtags})["data"]


def posts(account_id: str | None = None) -> list[dict]:
    q = f"?account_id={account_id}" if account_id else ""
    return _req("GET", f"/posts{q}")["data"]["posts"]
