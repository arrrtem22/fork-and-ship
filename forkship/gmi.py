"""GMI Cloud: an LLM writes the remake plan, a video model renders each shot."""
from __future__ import annotations

import json
import os
import time
import urllib.request

LLM_URL = "https://api.gmi-serving.com/v1/chat/completions"
VIDEO_URL = "https://console.gmicloud.ai/api/v1/ie/requestqueue/apikey"
LLM_MODEL = os.environ.get("GMI_LLM_MODEL", "google/gemini-3.8-flash")
VIDEO_MODEL = os.environ.get("GMI_VIDEO_MODEL", "seedance-2-0-fast-260128")


def _req(url: str, body: dict | None = None) -> dict:
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Authorization": f"Bearer {os.environ['GMI_API_KEY']}", "content-type": "application/json", "user-agent": "fork-and-ship/0.1"},
        method="POST" if body is not None else "GET",
    )
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.loads(r.read())


def chat_json(system: str, user) -> dict:
    """Ask the LLM for one JSON object."""
    r = _req(LLM_URL, {
        "model": LLM_MODEL,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "temperature": 0.7,
        "max_tokens": 16000,
        "response_format": {"type": "json_object"},
    })
    text = r["choices"][0]["message"]["content"].strip()
    if "</think>" in text:
        text = text.split("</think>", 1)[1]
    start, end = text.find("{"), text.rfind("}")
    return json.loads(text[start:end + 1])


def models() -> list[str]:
    return _req(f"{VIDEO_URL}/models").get("model_ids", [])


def model_params(model: str) -> list[dict]:
    return _req(f"{VIDEO_URL}/models/{model}").get("parameters", [])


def start_video(prompt: str, *, seconds: int = 5, model: str = VIDEO_MODEL, reference_images: list[str] | None = None) -> str:
    payload = {"prompt": prompt, "aspect_ratio": "9:16", "duration": seconds,
               "negative_prompt": "text, captions, watermark, logo, blurry, distorted hands"}
    if model.startswith("seedance"):
        payload = {"prompt": prompt, "ratio": "9:16", "resolution": "720p", "duration": seconds,
                   "watermark": False, "generate_audio": False}
        if reference_images:
            payload["reference_images"] = reference_images[:9]
    elif model.lower().startswith("veo"):
        payload = {"prompt": prompt, "aspectRatio": "9:16", "durationSeconds": str(seconds),
                   "negativePrompt": payload["negative_prompt"], "personGeneration": "allow_adult"}
    return _req(f"{VIDEO_URL}/requests", {"model": model, "payload": payload})["request_id"]


def wait_video(request_id: str, *, timeout_s: int = 600) -> str:
    """Block until the shot is rendered; returns the mp4 URL."""
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        r = _req(f"{VIDEO_URL}/requests/{request_id}")
        if r.get("status") in ("success", "finished", "completed"):
            out = r.get("outcome") or {}
            url = out.get("video_url") or next(
                (v for v in json.dumps(out).split('"') if v.startswith("https://") and ".mp4" in v), None)
            if url:
                return url
        if r.get("status") in ("failed", "error", "cancelled"):
            raise RuntimeError(f"GMI video {request_id} {r.get('status')}: {json.dumps(r.get('outcome'))[:300]}")
        time.sleep(5)
    raise TimeoutError(f"GMI video {request_id} not done in {timeout_s}s")


def start_music(prompt: str) -> str:
    """Instrumental bed for the video (MiniMax music on GMI)."""
    return _req(f"{VIDEO_URL}/requests", {"model": os.environ.get("GMI_MUSIC_MODEL", "minimax-music-3.0"), "payload": {
        "prompt": prompt + ", instrumental only, no vocals", "lyrics": "[Instrumental]\n(hum)\n[Instrumental]", "format": "mp3"}})["request_id"]


def wait_audio(request_id: str, *, timeout_s: int = 300) -> str:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        r = _req(f"{VIDEO_URL}/requests/{request_id}")
        if r.get("status") == "success":
            return (r.get("outcome") or {})["audio_url"]
        if r.get("status") in ("failed", "error", "cancelled"):
            raise RuntimeError(f"GMI music {request_id} {r.get('status')}")
        time.sleep(5)
    raise TimeoutError(request_id)
