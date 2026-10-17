---
name: talking-head-recut
description: |
  End-to-end workflow for recutting raw talking-head footage into high-engagement vertical short-form video (9:16).
  Includes local Whisper word-level transcription (zero ElevenLabs), multi-take selection, stumble/filler trimming,
  30ms audio crossfading, HyperFrames motion graphics (ProRes 4444 alpha overlays), subtitle-behind-graphics layering,
  automated Gemini / AI watermark removal (FFmpeg delogo), and social audio normalization (-14 LUFS).
license: MIT
metadata:
  version: "1.0.0"
---

# Talking-Head Recut & Motion Compositing Pipeline

This skill guides the complete process of transforming raw, unedited multi-take talking-head clips into a polished, high-retention 9:16 vertical video.

---

## Core Philosophy & Guardrails

1. **Local-First Whisper Transcription**:
   - Always run transcription locally via `mlx-whisper` (on Apple Silicon) or `faster-whisper`.
   - Never use ElevenLabs or external speech synthesis/re-voicing unless explicitly requested. Spoken words must remain genuine to the presenter.
2. **Pacing & Clean Cuts**:
   - Aggressively trim false starts, repeated words, filler pauses, and speech stumbles.
   - Smooth every clip boundary with a **30ms audio fade-in / fade-out** to eliminate micro-pops and clicks.
3. **65/35 Presentation Ratio**:
   - The presenter (A-roll) must be clearly visible ~65% of total runtime.
   - Motion graphics, diagrams, and scorecards occupy the remaining ~35%.
4. **Zero Face Occlusion**:
   - Graphic cards and badges sit in the upper background or lower third below the chest. Never cover the presenter's face or mouth.
   - Full-frame diagrams must use a blurred capture of the presenter's set as the backdrop.
5. **Subtitle Layering Contract**:
   - English / translated subtitles **must be placed behind** graphic layers.
   - Burn subtitles onto the base video stream first, then composite motion graphic overlays on top.
6. **Automated Watermark Removal**:
   - Detect and remove Gemini / AI logo watermarks in the corner using FFmpeg's `delogo` filter before final export.

---

## Directory Structure Pattern

When working on a talking-head project, organize files in the following layout:

```text
project/
├── raw/                      # Original recorded video takes (01.mp4, 02.mp4, ...)
├── edit/
│   ├── transcripts/          # Word-level Whisper JSON files for each raw clip
│   ├── takes_packed.md       # Consolidated markdown review with timestamps & takes
│   ├── clips_graded/         # Extracted trimmed cuts with 30ms audio fades
│   ├── base.mp4              # Concatenated trimmed talking-head base video
│   ├── master.srt            # Timecoded subtitles (English or translated)
│   ├── edl.json              # Edit Decision List defining cuts & graphic slots
│   ├── animations/           # HyperFrames motion graphics projects
│   │   ├── slot_01/          # Hook overlay (ProRes 4444 alpha render.mov)
│   │   ├── slot_04_05/       # Full diagram (Blurred backdrop render.mp4)
│   │   ├── slot_09/          # Scorecard animation
│   │   └── ...
│   ├── preview.mp4           # Rendered preview
│   └── final.mp4             # Final normalized, delogo'd export
```

---

## Step-by-Step Workflow

### Step 1: Local Whisper Word-Level Transcription

Extract audio and run word-level transcription locally.

```bash
# Using bundled skill script:
python ~/.gemini/config/skills/talking-head-recut/scripts/transcribe_local.py raw/*.mp4 \
  --output-dir edit/transcripts \
  --model mlx-community/whisper-large-v3-turbo \
  --summary edit/takes_packed.md
```

This generates:
- Per-clip JSON transcripts with word-level timestamps (`start`, `end`, `probability`).
- A consolidated `takes_packed.md` table showing all takes and timestamps for easy take comparison.

---

### Step 2: Take Selection & Cut Decision List (`edl.json`)

Analyze `takes_packed.md` to:
1. Choose the best take when multiple takes exist for a section.
2. Identify exact timestamps to cut out false starts and verbal stumbles (e.g. cutting out `0.0s - 0.22s` of a clip if the speaker stuttered).
3. Record all cuts and overlays in `edit/edl.json`:

```json
{
  "sources": {
    "01": "raw/01.mp4",
    "02": "raw/02.mp4"
  },
  "ranges": [
    { "source": "01", "start": 0.0, "end": 3.40, "quote": "Opening hook line" },
    { "source": "02", "start": 0.5, "end": 5.75, "quote": "Core argument without stumble" }
  ],
  "overlays": [
    {
      "file": "edit/animations/slot_01/render.mov",
      "start_in_output": 0.0,
      "duration": 3.4
    }
  ],
  "subtitles": "edit/master.srt"
}
```

---

### Step 3: HyperFrames Motion Graphics & Render Contract

Build motion graphics using HyperFrames HTML/CSS/GSAP.

#### 1. Design System & Palette
- **Canvas**: 9:16 vertical (720x1280 or 1080x1920)
- **Backgrounds**: Deep Space Navy (`#0B192C`), Midnight Slate (`#132043`)
- **Accents**: Neon Cyan (`#00D2DF`), Cyber Teal (`#14b8a6`)
- **Text & Borders**: Warm White (`#F8F9FA`), Translucent Glass (`rgba(255,255,255,0.08)`)
- **Typography**: Bold Sans-Serif (`-apple-system`, `BlinkMacSystemFont`, `Inter`)

#### 2. Alpha Transparency Rule (Crucial)
- **DO NOT** use `--format webm` for transparent video overlays intended for FFmpeg compositing (FFmpeg decodes VP9 with `ALPHA_MODE: 1` as `yuv420p` without an alpha plane, causing solid black backgrounds).
- **ALWAYS** render transparent overlays as **ProRes 4444 `.mov`**:
  ```bash
  hyperframes render . --format mov -o render.mov
  ```
  This outputs `yuva444p12le`, which FFmpeg decodes and overlays with pixel-perfect transparency over the speaker.

#### 3. Blurred A-Roll Backdrops
For full-frame diagrams (where speaker is not on camera):
- Extract a clean frame from the speaker's scene:
  ```bash
  ffmpeg -y -ss 2.0 -i raw/04.mp4 -vf "scale=720:1280,boxblur=15:5" -vframes 1 edit/animations/slot_04_05/bg.jpg
  ```
- Use `bg.jpg` with a dark gradient overlay in the HyperFrames composition. Render directly as high-efficiency MP4 (`--format mp4`).

---

### Step 4: Subtitles & Layering Contract

Create `edit/master.srt`. Ensure timestamps align with the reassembled cut timeline (`base.mp4`).

In FFmpeg, execute the strict layering contract:
1. Base talking head (`[0:v]`)
2. Remove Gemini/AI watermark (`delogo`)
3. Subtitle filter (`subtitles='master.srt'`)
4. HyperFrames overlays (`overlay=enable='between(t,...)'`)

```text
[0:v] -> delogo -> subtitles -> [subv]
[subv] + [overlay_1] -> [v1]
[v1]   + [overlay_2] -> [v2] -> final video
```

---

### Step 5: Gemini & AI Watermark Removal (`delogo`)

Gemini-generated video clips contain a four-pointed star logo in the bottom-right corner.

#### Coordinates Reference
- **720 x 1280 resolution**:
  - `x = 566`
  - `y = 1130`
  - `w = 68`
  - `h = 75`
- **1080 x 1920 resolution** (1.5x scale):
  - `x = 849`
  - `y = 1695`
  - `w = 102`
  - `h = 113`

#### Standalone Removal Command
```bash
python ~/.gemini/config/skills/talking-head-recut/scripts/delogo.py edit/base.mp4 -o edit/base_clean.mp4 --verify
```

#### Integrated FFmpeg Filter
```text
delogo=x=566:y=1130:w=68:h=75
```
FFmpeg interpolates pixels around the bounding box, leaving zero trace of the watermark.

---

### Step 6: Audio Processing & Social Normalization

1. **30ms Audio Crossfading on Cuts**:
   ```text
   -af "afade=t=in:st=0:d=0.03,afade=t=out:st=<dur-0.03>:d=0.03"
   ```
2. **Social Loudness Normalization**:
   Apply EBU R128 loudness normalization for Reels/TikTok/Shorts:
   ```bash
   ffmpeg -y -i preview_raw.mp4 \
     -c:v copy \
     -af "loudnorm=I=-14:TP=-1:LRA=11" \
     -c:a aac -b:a 192k -ar 48000 \
     -movflags +faststart \
     final.mp4
   ```

---

### Step 7: Automated Master Pipeline Execution

Execute the all-in-one pipeline script:

```bash
python ~/.gemini/config/skills/talking-head-recut/scripts/pipeline.py \
  --edl edit/edl.json \
  -o edit/final.mp4
```

This single command:
1. Cuts raw segments and applies 30ms audio fades.
2. Assembles `base.mp4`.
3. Delogos the watermark.
4. Burns `master.srt` behind graphic layers.
5. Composites all HyperFrames `.mov` and `.mp4` overlays.
6. Normalizes audio to -14 LUFS.

---

## Reusable Templates Included

- `templates/hyperframes/hook-card/`: Transparent floating hook title card.
- `templates/hyperframes/diagram-7pillars/`: 7-point staggered pillar cards with blurred A-roll background.
- `templates/hyperframes/scorecard/`: Interactive 1-to-5 scorecard assessment card.
- `templates/hyperframes/key-protocol/`: 2-step actionable protocol card with glow effects.
- `templates/hyperframes/cta-outro/`: End-of-video pulsing call-to-action overlay.
