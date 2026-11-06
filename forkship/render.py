"""Turn a remake plan into one 9:16 mp4: rendered shots, TikTok-style text on top, app end card."""
from __future__ import annotations

import concurrent.futures as cf
import os
import subprocess
import textwrap
import urllib.request

from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1920
FONT = os.environ.get("FORKSHIP_FONT", "/System/Library/Fonts/Supplemental/Arial Bold.ttf")


def text_png(text: str, out: str, *, y_frac: float = 0.22, size: int = 74) -> str:
    """White words, black outline, upper third: the look Oriane reads on the winners' frames."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    font = ImageFont.truetype(FONT, size)
    lines = textwrap.wrap(text, max(12, int(22 * 74 / size)))[:6]
    y = int(H * y_frac) - (len(lines) * int(size * 1.25)) // 2 if y_frac > 0.3 else int(H * y_frac)
    for line in lines:
        w = d.textlength(line, font=font)
        d.text(((W - w) / 2, y), line, font=font, fill="white", stroke_width=7, stroke_fill="black")
        y += int(size * 1.25)
    img.save(out)
    return out


def _ff(*args: str) -> None:
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *args], check=True)


def shot_clip(src: str, overlay_text: str, seconds: float, out: str, work: str, *, y_frac: float = 0.22, size: int = 74) -> str:
    """Fit a source clip (mp4) or still (jpg/png) to 9:16 for `seconds`, with the shot's on-screen text."""
    png = text_png(overlay_text, os.path.join(work, os.path.basename(out) + ".txt.png"), y_frac=y_frac, size=size) if overlay_text else None
    is_still = src.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))
    inputs = (["-loop", "1", "-t", str(seconds), "-i", src] if is_still else ["-stream_loop", "-1", "-t", str(seconds), "-i", src])
    fit = f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1,fps=30,format=yuv420p"
    if png:
        _ff(*inputs, "-i", png, "-filter_complex", f"[0:v]{fit}[b];[b][1:v]overlay=0:0,format=yuv420p[v]",
            "-map", "[v]", "-t", str(seconds), "-an", "-c:v", "libx264", "-preset", "veryfast", out)
    else:
        _ff(*inputs, "-vf", fit, "-t", str(seconds), "-an", "-c:v", "libx264", "-preset", "veryfast", out)
    return out


def concat(clips: list[str], out: str) -> str:
    args: list[str] = []
    for c in clips:
        args += ["-i", c]
    n = len(clips)
    _ff(*args, "-filter_complex", "".join(f"[{i}:v]" for i in range(n)) + f"concat=n={n}:v=1:a=0[v]",
        "-map", "[v]", "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p", "-movflags", "+faststart", out)
    return out


def render_shots(shots: list[dict], work: str, generate) -> list[str]:
    """Render every shot at once; `generate(prompt, seconds)` returns an mp4 URL or a local still path."""
    os.makedirs(work, exist_ok=True)

    def one(i_shot):
        i, s = i_shot
        src = generate(s["prompt"], int(s.get("seconds", 5)))
        if src.startswith("http"):
            local = os.path.join(work, f"raw_{i}.mp4")
            urllib.request.urlretrieve(src, local)
            src = local
        return shot_clip(src, s.get("on_screen_text", ""), float(s.get("seconds", 5)), os.path.join(work, f"shot_{i}.mp4"), work,
                         y_frac=float(s.get("text_y", 0.22)), size=int(s.get("text_size", 74)))

    with cf.ThreadPoolExecutor(max_workers=4) as ex:
        return list(ex.map(one, enumerate(shots)))


def add_music(video: str, audio: str, out: str, seconds: float) -> str:
    _ff("-i", video, "-i", audio, "-filter_complex",
        f"[1:a]atrim=0:{seconds},afade=t=in:d=0.3,afade=t=out:st={max(0, seconds - 0.8)}:d=0.8,volume=0.8[a]",
        "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", out)
    return out
