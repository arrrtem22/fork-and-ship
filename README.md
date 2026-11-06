# Fork & Ship

Find the video format that is winning in your niche this week, remake it for your product, post it, and let the views pick the next one.

Built at Hack the Feed (Amplitude HQ, Nov 6 2026) on Oriane, GMI Cloud and Outnumber.

```
Oriane ──► winners in the niche, read second by second (what they say, show, sound like)
  │
GMI LLM ──► names the formats, picks one, writes the remake shot by shot
  │
GMI video model (Kling / Veo) ──► renders each shot, ffmpeg adds the on-screen text + app end card
  │
Outnumber API ──► uploads the mp4 and queues it on a TikTok account
  │
Outnumber API ──► reads the views back ──► next plan sees what worked
```

## What Oriane gives us per video

- spoken hook: transcript chunks with start times, so we know what is said in the first 3 seconds
- on-screen text per frame with timestamps, so we know when the first text lands and how often it changes
- audio track title and author, duration, words per second
- views, followers, views per follower

We rank by **views per follower**. A 5K-follower account with a 500K-view video proves the format, not the fame.

## Run

Python 3.11+, Pillow, ffmpeg.

```bash
export ORIANE_API_KEY=...      # connect.oriane.xyz
export GMI_API_KEY=...         # console.gmicloud.ai
export OUTNUMBER_API_KEY=onk_... # useoutnumber.com, Settings > API keys (optional: skip to only render)

python -m forkship.agent loop    # learn -> research -> plan -> render -> ship
python -m forkship.report        # data/index.html, the dashboard
```

Steps run one at a time too: `research`, `plan`, `render`, `ship`, `learn`.
Edit `product.json` for your own product and niche.

## Files

- `forkship/oriane.py`: search + turn each video into hook, text timeline, sound, pacing
- `forkship/gmi.py`: LLM plan (OpenAI-style chat) and the video request queue
- `forkship/render.py`: 9:16 shots, text overlay, concat
- `forkship/outnumber.py`: upload, queue, read views
- `forkship/agent.py`: the loop
- `forkship/report.py`: the demo page
