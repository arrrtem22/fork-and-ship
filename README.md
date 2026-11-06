# Fork & Ship

Find the video that is winning in your niche this week, fork it for your product, post it, and let the views pick the next one.

Built at Hack the Feed (Amplitude HQ, Nov 6 2026) on Oriane, GMI Cloud and Outnumber.

## Fork mode (`python -m forkship.agent fork`)

1. Oriane ranks the niche's videos by views per follower and picks the top one with a clear shot structure.
2. Each shot of the original is re-shot by GMI's Seedance model. The original frame goes in as a reference with its on-screen text blurred out using Oriane's text boxes, so the model keeps the framing, action and cut length but not the creator's face, plate or caption.
3. The split by screen time:
   - about 80% copy: same shots, same cut timing, the original's on-screen text nearly word for word, in the creator's text position and size
   - about 10% test: one experiment, a new hook line on shot 1, logged so the views decide if it stays
   - about 10% CTA: the last beat is the real app screen with one line in the creator's voice
4. GMI's MiniMax music model makes an instrumental bed, and ffmpeg mixes it in.

Example run: a 7-second "a meal I could eat 5 days a week in a calorie deficit" (641K views on 27K followers) became a 9.5-second fork ending on a calorie-tracker app.

## Full loop

```
Oriane ──► winners in the niche, read second by second (what they say, show, sound like)
  │
GMI LLM ──► names the formats, picks one, writes the remake shot by shot
  │
GMI video model (Seedance 2.0) ──► renders each shot, ffmpeg adds the on-screen text + app end card
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

python -m forkship.agent research   # Oriane winners -> data/research.json
python -m forkship.agent fork       # fork the best one -> data/fork_<time>.mp4
python -m forkship.agent loop       # learn -> research -> plan -> render -> ship (original-format remake)
python -m forkship.report        # data/index.html, the dashboard
```

Steps run one at a time too: `research`, `plan`, `render`, `fork`, `music`, `ship`, `learn`.
Put real screenshots of your app in `assets/product_*.jpg` (video models garble app screens).
Edit `product.json` for your own product and niche.

## Files

- `forkship/oriane.py`: search + turn each video into hook, text timeline, sound, pacing
- `forkship/fork.py`: the fork plan (vision model reads the original's frames) and text-free reference frames
- `forkship/gmi.py`: LLM plan (OpenAI-style chat), video and music request queue
- `forkship/render.py`: 9:16 shots, text overlay, concat
- `forkship/outnumber.py`: upload, queue, read views
- `forkship/agent.py`: the loop
- `forkship/report.py`: the demo page
