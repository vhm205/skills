---
name: vertical-shorts-pipeline
description: >
  Produce short-form videos (9:16, 1:1, or 16:9) from a script + screen
  recording. Generates voiceover with Kokoro TTS (local, free, English) or Edge
  TTS (any locale incl. Vietnamese), extracts word-level timings, auto-fits the
  recording to the frame (contain / cover / cover-pan zoom), and outputs a
  HyperFrames composition ready to render as MP4.
---

# Vertical Shorts Pipeline

Turn a script and a screen recording into a publishable vertical video with
voiceover, captions, and screen recording — all automated, no GUI editing.

## What it does

1. **Voiceover generation** — Kokoro TTS (local, free, English, 82M-param) or
   Edge TTS (network, ~100 locales incl. Vietnamese). 20+ Kokoro voices + all
   edge-tts voices available.
2. **Word-level timing** — Whisper transcribes the generated audio and aligns
   timestamps word-by-word against your script, producing frame-accurate
   caption data. For cross-language voiceover/captions, caption words are
   distributed proportionally across the narration's segment boundaries.
3. **Screen recording alignment** — The recording is segmented and
   speed-adjusted so each visual segment matches its narration segment. No
   manual trimming needed.
4. **HyperFrames composition** — An HTML template with:
   - Screen recording area, auto-fitted to the frame (contain / cover / cover-pan)
   - Rolling word-level captions with highlight
   - Room for text/diagram overlays
   - Narration audio track
5. **Render** — `npx hyperframes render` produces the final MP4.

## Quick start

```bash
python scripts/pipeline.py \
  --script my_script.txt \
  --recording my_demo.mp4 \
  --output-dir ./output \
  --title "My Video Title"
```

Then:
```bash
cd output/hyperframes
npx hyperframes check
npx hyperframes preview --background   # review
npx hyperframes render --quality high --output renders/video.mp4
```

## Per-video inputs

You provide **three** things per video:

| Input | Description |
|-------|-------------|
| `--script` | Text file with the caption text (and narration text, unless `--narration` is given) |
| `--recording` | MP4 screen recording of the demo/tool |
| `--title` | Video title |

Optional:
| Flag | Default | Description |
|------|---------|-------------|
| `--voice` | auto | TTS voice. For Kokoro: `af_heart`, `af_bella`, `af_nicole`, `af_sarah`, `af_sky`, `am_adam`, `am_michael`, `am_eric`, `am_liam`, `am_jesse`, `bf_emma`, `bf_isabella`, `bf_alice`, `bf_lily`, `bm_george`, `bm_lewis`, `bm_daniel`, `bm_oliver`. For Edge: any edge-tts `ShortName` (e.g. `vi-VN-HoaiMyNeural`, `en-US-AriaNeural`). |
| `--tts-engine` | `kokoro` | `kokoro` (local, English-only) or `edge` (network, ~100 locales incl. Vietnamese) |
| `--voice-lang` | `en` | Language code for TTS + Whisper transcription (`en`, `vi`, …) |
| `--narration` | none | Voiceover text file when it differs from captions (see "Foreign-language voiceover" below) |
| `--aspect` | `9:16` | Output frame: `9:16`, `1:1`, `16:9`, or `WxH` (e.g. `1080x1350`) |
| `--fit` | `contain` | How the recording fills the frame: `contain`, `cover`, `cover-pan` (see below) |
| `--speed` | `1.0` | TTS speed (0.5–2.0) |
| `--skip-tts` | false | Skip TTS (use existing voiceover.wav) |
| `--skip-timing` | false | Skip word timing (use existing timing.json) |
| `--skip-align` | false | Skip recording alignment |

## Aspect ratio & auto-fit (zoom to fill)

Desktop/web screen recordings are almost always 16:9 landscape. Short-form
platforms want **9:16** (Shorts/TikTok/Reels), **1:1** (feed squares), or
**16:9** (YouTube landscape). The `--aspect` flag sets the output frame, and
`--fit` controls how the recording is adapted to it:

| `--fit` | Behaviour | When to use |
|---------|-----------|-------------|
| `contain` (default) | Letterbox the recording — nothing is cropped. In portrait/square frames it sits in a 16:9-shaped band at the top, with captions in the space below. | When the whole screen must stay visible (code demos, full-UI walkthroughs). |
| `cover` | Zoom the recording until it fills the frame, cropping whatever overflows (centre-anchored). | When you want the recording to fill the frame edge-to-edge and don't mind losing the extreme edges. |
| `cover-pan` | `cover` plus a slow pan (Ken Burns) so the crop travels across the shot over the whole duration. | Best of both: fills the frame *and* reveals more of a wide recording over time. |

All three are implemented with CSS `object-fit` (`contain`/`cover`) and, for
`cover-pan`, an animated `object-position` — no FFmpeg re-encode of the
recording, so the segments are generated once and any fit mode works off the
same clips.

Example — a 16:9 screen recording into a square feed post that slowly pans:

```bash
python scripts/pipeline.py \
  --script my_script.txt \
  --recording my_demo.mp4 \
  --output-dir ./output \
  --aspect 1:1 \
  --fit cover-pan \
  --title "My Square Post"
```

## Foreign-language voiceover (e.g. Vietnamese audio + English captions)

The default `kokoro` engine is **English-only** (`en-us`/`en-gb` voices). For a
voiceover in another language, switch to the **Edge TTS** engine, which exposes
~100 locales:

```bash
python scripts/pipeline.py \
  --script captions_en.txt \      # English subtitles shown on screen
  --narration narration_vi.txt \  # Vietnamese text spoken as voiceover
  --recording my_demo.mp4 \
  --tts-engine edge \
  --voice vi-VN-HoaiMyNeural \    # female; vi-VN-NamMinhNeural is male
  --voice-lang vi \
  --output-dir ./output
```

How it works:
- `--narration` is the text the voiceover reads (any language Edge supports).
- `--script` remains the **caption** text (any language you want on screen).
- Whisper transcribes the *audio* (in `--voice-lang`) to get segment timing,
  then distributes the caption words across those segments proportionally.

> Note: across languages, captions advance in lockstep with the narration but
> word-for-word highlighting is approximate — exact word-sync isn't meaningful
> when the spoken and written languages differ. For same-language voiceover and
> captions, keep the default edit-distance alignment (leave `--narration`
> unset), which gives frame-accurate word highlighting.

This also works in reverse (English voiceover, Vietnamese subtitles): put the
English text in `--narration` and the Vietnamese text in `--script`.

## Voiceover: why Kokoro

The pipeline uses **Kokoro TTS** via the `kokoro-onnx` package:
- **Local only** — runs entirely on your machine, no API calls, no per-request cost
- **82M parameters** — lightweight enough for CPU inference (~real-time on modern hardware)
- **Apache 2.0 licensed** — no usage restrictions
- **20+ voices** — male and female, multiple accents (American, British)
- **~310 MB model** — downloaded once, cached at `%LOCALAPPDATA%\hermes\models\kokoro\`

**Voice cloning** (your second option) is not included in this version.
Open-source voice cloning (Coqui TTS, OpenVoice, etc.) requires a 10–30 minute
clean voice sample and significantly more GPU memory. This pipeline opts for
Kokoro's ready-to-use voices as the practical first step; if you later record
voice samples, we can add a cloning step.

## Word-level timing

The pipeline uses **OpenAI Whisper** (`tiny` model) to transcribe the generated
audio with word-level timestamps, then aligns them against your script using
edit-distance (Levenshtein) matching. This approach:
- Works with the exact audio that will play (not estimated from text)
- Handles pronunciation variations gracefully
- Produces frame-accurate `{word, start, end}` entries for caption animation

## Output structure

```
output/
├── voiceover.wav              # Generated TTS audio
├── timing.json                # Word-level timestamps
├── recording_segments/        # Aligned recording clips
│   ├── seg_000.mp4
│   ├── seg_001.mp4
│   └── ...
├── render_config.json         # Pipeline metadata
└── hyperframes/
    ├── index.html             # HyperFrames composition
    └── assets/
        ├── voiceover.wav
        ├── timing.json
        └── seg_*.mp4
```

## Editing the composition

The generated `index.html` is a standard HyperFrames composition. You can:
- **Add text overlays**: Place HTML inside the `.overlay-area` div
- **Adjust caption style**: Edit the CSS `--caption-*` variables
- **Change layout**: The screen recording area, captions, and overlay are
  separate positioned regions
- **Add transitions**: Use the HyperFrames transition catalog

## Prerequisites

- **Python 3.10+** with packages:
  - `kokoro-onnx` (Kokoro TTS, English)
  - `edge-tts` (Edge TTS, any locale — needed for non-English voiceover)
  - `openai-whisper` (word timing)
  - `soundfile`, `numpy`
- **FFmpeg** on PATH (for recording alignment + Edge audio conversion). The
  script auto-locates a winget/scoop/chocolatey install if it's not on PATH.
- **Node.js 22+** (for HyperFrames)
- **HyperFrames CLI**: `npm install -g hyperframes` or use `npx hyperframes`

Install Python deps:
```bash
pip install kokoro-onnx edge-tts openai-whisper soundfile numpy
```

Download Kokoro models (if not auto-downloaded):
```bash
python -c "
import urllib.request, os
d = os.path.join(os.environ['LOCALAPPDATA'], 'hermes', 'models', 'kokoro')
os.makedirs(d, exist_ok=True)
urllib.request.urlretrieve('https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.1/kokoro-v1.0.onnx', os.path.join(d, 'kokoro-v1.0.onnx'))
urllib.request.urlretrieve('https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.1/voices-v1.0.bin', os.path.join(d, 'voices-v1.0.bin'))
"
```

## Troubleshooting

| Problem | Fix |
|---------|-----|
| "Kokoro model not found" | Run the download script above |
| FFmpeg not found | `winget install Gyan.FFmpeg` |
| Whisper OOM on CPU | The `tiny` model uses ~1 GB RAM; use `--skip-timing` if needed |
| Recording too short | Pipeline auto-freezes last frame |
| Recording too long | Pipeline trims segments proportionally |