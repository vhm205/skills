#!/usr/bin/env python3
"""
Vertical Shorts Pipeline — script + screen recording → HyperFrames vertical video.

One command:
  python scripts/pipeline.py --script SCRIPT.txt --recording DEMO.mp4 --output-dir ./out

Produces a HyperFrames composition (default 1080×1920) with voiceover,
word-level captions, and aligned screen recording segments.

Features:
  --aspect  9:16 | 1:1 | 16:9 | <W>x<H>   output frame size (default 9:16)
  --fit     contain | cover | cover-pan   how the recording fills the frame
  --tts-engine  kokoro | edge             voiceover backend
  --narration FILE                        voiceover text when it differs from captions
                                          (e.g. Vietnamese voiceover + English subtitles)
  --voice-lang LANG                       TTS + Whisper language code (e.g. "vi", "en")
"""

import argparse
import asyncio
import json
import os
import re
import subprocess
import sys
from pathlib import Path

KOKORO_MODEL_DIR = os.path.join(
    os.environ.get("LOCALAPPDATA", os.path.expanduser("~/.local/share")),
    "hermes", "models", "kokoro"
)

KOKORO_VOICES = [
    "af_heart", "af_bella", "af_nicole", "af_sarah", "af_sky",
    "am_adam", "am_michael", "am_eric", "am_liam", "am_jesse",
    "bf_emma", "bf_isabella", "bf_alice", "bf_lily",
    "bm_george", "bm_lewis", "bm_daniel", "bm_oliver",
]

# Default edge-tts voices per language (fallback when --voice not given).
EDGE_DEFAULT_VOICE = {
    "vi": "vi-VN-HoaiMyNeural",   # Vietnamese (female)
    "en": "en-US-AriaNeural",     # English (female)
}

ASPECTS = {"9:16": (1080, 1920), "1:1": (1080, 1080), "16:9": (1920, 1080)}
FITS = ("contain", "cover", "cover-pan")


def find_ffmpeg() -> str:
    """Locate ffmpeg on Windows, falling back to common install locations.

    FFmpeg is often installed via winget/scoop/chocolatey and shimmed onto PATH;
    when the shim directory is empty (a known winget quirk), PATH lookup fails.
    """
    import shutil
    exe = shutil.which("ffmpeg")
    if exe:
        return exe

    candidates = [
        os.path.join(os.environ.get("LOCALAPPDATA", ""),
                     "Microsoft", "WinGet", "Links", "ffmpeg.exe"),
        os.path.join(os.environ.get("LOCALAPPDATA", ""),
                     "Microsoft", "WinGet", "Packages"),
        os.path.join(os.environ.get("USERPROFILE", ""), "scoop", "shims", "ffmpeg.exe"),
        os.path.join(os.environ.get("ProgramData", ""), "chocolatey", "bin", "ffmpeg.exe"),
    ]
    for c in candidates:
        if c.endswith("ffmpeg.exe") and os.path.exists(c):
            return c
    # Search the WinGet Packages tree for any Gyan.FFmpeg install.
    pkg_root = candidates[1]
    if os.path.isdir(pkg_root):
        for root, dirs, files in os.walk(pkg_root):
            if "ffmpeg.exe" in files:
                return os.path.join(root, "ffmpeg.exe")
    return "ffmpeg"  # last resort: rely on PATH at call time


FFMPEG = find_ffmpeg()
FFPROBE = FFMPEG.replace("ffmpeg.exe", "ffprobe.exe") if FFMPEG.endswith("ffmpeg.exe") else \
    (FFMPEG.replace("ffmpeg", "ffprobe"))

# Whisper's load_audio() calls `ffmpeg` by name (not path), so put the resolved
# ffmpeg's directory on PATH when it lives outside the standard path.
if os.path.sep in FFMPEG:
    _ffdir = os.path.dirname(FFMPEG)
    if _ffdir not in os.environ.get("PATH", ""):
        os.environ["PATH"] = _ffdir + os.pathsep + os.environ.get("PATH", "")


# ═══════════════════════════════════════════════════════════════════════════════
# Step 1: Voiceover (Kokoro local, or Edge TTS for non-English)
# ═══════════════════════════════════════════════════════════════════════════════

def generate_voiceover(script_text: str, output_path: str, voice: str = "af_heart",
                       speed: float = 1.0, engine: str = "kokoro",
                       lang: str = "en-us") -> dict:
    if engine == "edge":
        return _generate_voiceover_edge(script_text, output_path, voice, speed, lang)
    return _generate_voiceover_kokoro(script_text, output_path, voice, speed)


def _generate_voiceover_kokoro(script_text, output_path, voice, speed):
    model_path = os.path.join(KOKORO_MODEL_DIR, "kokoro-v1.0.onnx")
    voices_path = os.path.join(KOKORO_MODEL_DIR, "voices-v1.0.bin")
    if not os.path.exists(model_path) or not os.path.exists(voices_path):
        raise FileNotFoundError(
            f"Kokoro models not found in {KOKORO_MODEL_DIR}. "
            "Download from https://github.com/thewh1teagle/kokoro-onnx/releases"
        )
    from kokoro_onnx import Kokoro
    import soundfile as sf
    import numpy as np

    kokoro = Kokoro(model_path, voices_path)
    samples, sample_rate = kokoro.create(script_text, voice=voice, speed=speed, lang="en-us")
    if samples.dtype != np.float32:
        samples = samples.astype(np.float32)
    sf.write(output_path, samples, sample_rate)
    return {
        "path": output_path, "sample_rate": sample_rate,
        "duration_s": round(len(samples) / sample_rate, 3),
        "voice": voice, "speed": speed, "engine": "kokoro",
    }


def _generate_voiceover_edge(script_text, output_path, voice, speed, lang):
    """Edge TTS (needs network). Supports ~100 locales incl. Vietnamese.

    edge_tts always writes an MP3 (regardless of file extension), so write to a
    temp .mp3 first, then convert to a 16-bit mono WAV via FFmpeg (Whisper is
    happy with wav, and the composition's <audio> plays it reliably)."""
    import edge_tts

    if not voice:
        voice = EDGE_DEFAULT_VOICE.get(lang.split("-")[0], "en-US-AriaNeural")

    rate = f"{int(round((speed - 1.0) * 100)):+d}%"

    # edge_tts always writes MP3 regardless of file extension, so save to a
    # temp .mp3 first, then convert to a 16-bit mono WAV (Whisper-friendly, and
    # the composition's <audio> plays wav reliably).
    mp3_path = output_path[:-4] + ".tmp.mp3" if output_path.lower().endswith(".wav") \
        else output_path + ".tmp.mp3"

    async def _run():
        communicate = edge_tts.Communicate(script_text, voice, rate=rate)
        await communicate.save(mp3_path)

    asyncio.run(_run())

    subprocess.run([
        FFMPEG, "-y", "-i", mp3_path, "-ar", "24000", "-ac", "1",
        "-c:a", "pcm_s16le", output_path,
    ], capture_output=True, check=False)
    if os.path.exists(mp3_path):
        os.remove(mp3_path)

    import soundfile as sf
    info = sf.info(output_path)
    return {
        "path": output_path, "sample_rate": info.samplerate,
        "duration_s": round(info.duration, 3),
        "voice": voice, "speed": speed, "engine": "edge",
    }


# ═══════════════════════════════════════════════════════════════════════════════
# Step 2: Word-level timing via Whisper
# ═══════════════════════════════════════════════════════════════════════════════

def extract_word_timings(audio_path: str, reference_text: str,
                         output_path: str, lang: str = "en",
                         narration_text: str = None) -> list:
    """Whisper transcribes the *audio*, then timestamps the caption text.

    - Same-language (narration_text is None or equals reference_text): align
      caption words against Whisper's word timestamps via edit distance.
    - Cross-language (narration_text differs): Whisper gives segment boundaries
      in the narration language; caption words are distributed across those
      segments proportionally. Exact word-sync across languages is not
      meaningful, but captions advance in lockstep with the narration.
    """
    import whisper

    model = whisper.load_model("tiny")
    result = model.transcribe(audio_path, word_timestamps=True, language=lang,
                              verbose=False)

    caption_raw = re.findall(r"[a-zA-Z0-9'\u00C0-\u024F]+", reference_text)
    caption_lower = [w.lower() for w in caption_raw]

    cross_lang = bool(narration_text) and narration_text.strip() != reference_text.strip()

    if cross_lang:
        aligned = _distribute_across_segments(result, caption_raw)
    else:
        whisper_words = []
        for seg in result.get("segments", []):
            for wi in seg.get("words", []):
                w = wi.get("word", "").strip().strip(".,!?;:")
                if w:
                    whisper_words.append({
                        "word": w.lower(), "start": round(wi["start"], 3),
                        "end": round(wi["end"], 3),
                    })
        aligned = _align_dp(caption_lower, caption_raw, whisper_words)

    with open(output_path, "w") as f:
        json.dump(aligned, f, indent=2)
    return aligned


def _distribute_across_segments(result, caption_words):
    """Split caption words evenly across the narration's Whisper segments."""
    segs = result.get("segments", [])
    if not segs or not caption_words:
        return _fallback_timings(caption_words)

    # Build per-segment word budget proportional to segment duration.
    total = sum(max(0, s["end"] - s["start"]) for s in segs)
    budgets = []
    for s in segs:
        d = max(0.01, s["end"] - s["start"])
        budgets.append(max(1, round(len(caption_words) * d / total)))

    aligned = []
    wi = 0
    for si, seg in enumerate(segs):
        n = budgets[si]
        start = seg["start"]
        end = seg["end"]
        # last segment absorbs any remainder
        if si == len(segs) - 1:
            n = len(caption_words) - wi
        step = (end - start) / max(1, n)
        for k in range(n):
            if wi >= len(caption_words):
                break
            aligned.append({
                "word": caption_words[wi],
                "start": round(start + k * step, 3),
                "end": round(start + (k + 1) * step, 3),
            })
            wi += 1
    return aligned


def _align_dp(ref_lower, ref_raw, whisper_words):
    """DP edit-distance alignment: ref words → whisper timestamps."""
    if not whisper_words:
        return _fallback_timings(ref_raw)

    nr, nw = len(ref_lower), len(whisper_words)
    INF = float("inf")
    dp = [[INF] * (nw + 1) for _ in range(nr + 1)]
    dp[0][0] = 0
    for j in range(1, nw + 1):
        dp[0][j] = j
    for i in range(1, nr + 1):
        dp[i][0] = i

    for i in range(1, nr + 1):
        for j in range(1, nw + 1):
            cost = 0 if ref_lower[i - 1] == whisper_words[j - 1]["word"] else 1
            dp[i][j] = min(dp[i - 1][j - 1] + cost, dp[i - 1][j] + 1, dp[i][j - 1] + 1)

    i, j = nr, nw
    ref_to_wsp = {}
    while i > 0 and j > 0:
        cost = 0 if ref_lower[i - 1] == whisper_words[j - 1]["word"] else 1
        if dp[i][j] == dp[i - 1][j - 1] + cost:
            if cost == 0:
                ref_to_wsp[i - 1] = j - 1
            i -= 1; j -= 1
        elif dp[i][j] == dp[i - 1][j] + 1:
            i -= 1
        else:
            j -= 1

    aligned = []
    for ri in range(nr):
        if ri in ref_to_wsp:
            wi = ref_to_wsp[ri]
            aligned.append({"word": ref_raw[ri], "start": whisper_words[wi]["start"],
                            "end": whisper_words[wi]["end"]})
        else:
            prev = aligned[-1]["end"] if aligned else 0
            aligned.append({"word": ref_raw[ri], "start": round(prev, 3),
                            "end": round(prev + 0.3, 3)})
    return aligned


def _fallback_timings(words):
    t = 0.0
    result = []
    for w in words:
        result.append({"word": w, "start": round(t, 3), "end": round(t + 0.3, 3)})
        t += 0.3
    return result


# ═══════════════════════════════════════════════════════════════════════════════
# Step 3: Screen recording alignment
# ═══════════════════════════════════════════════════════════════════════════════

def group_timing_into_segments(timing_data: list, max_dur: float = 2.5) -> list:
    segs = []
    cur = {"words": [], "start": None, "end": None}
    for w in timing_data:
        if cur["start"] is None:
            cur["start"] = w["start"]
        cur["words"].append(w)
        cur["end"] = w["end"]
        if cur["end"] - cur["start"] >= max_dur or w == timing_data[-1]:
            segs.append({
                "start": cur["start"], "end": cur["end"],
                "duration": round(cur["end"] - cur["start"], 3),
                "word_count": len(cur["words"]),
            })
            cur = {"words": [], "start": None, "end": None}
    return segs


def align_recording(recording_path: str, timing_data: list, output_dir: str,
                    total_duration: float) -> dict:
    os.makedirs(output_dir, exist_ok=True)

    result = subprocess.run(
        [FFPROBE, "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", recording_path],
        capture_output=True, text=True)
    rec_dur = float(result.stdout.strip())

    segments = group_timing_into_segments(timing_data, max_dur=2.5)
    seg_files = []

    for i, seg in enumerate(segments):
        seg_dur = seg["end"] - seg["start"]
        progress_s = seg["start"] / total_duration if total_duration > 0 else 0
        progress_e = seg["end"] / total_duration if total_duration > 0 else 1
        rec_start = progress_s * rec_dur
        rec_end = min(progress_e * rec_dur, rec_dur)
        available = max(0, rec_end - rec_start)

        out_file = os.path.join(output_dir, f"seg_{i:03d}.mp4")

        if available < 0.1:
            # Freeze on the last frame for the segment duration.
            subprocess.run([
                FFMPEG, "-y", "-ss", str(max(0, rec_dur - 1)),
                "-i", recording_path, "-frames:v", "1",
                "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
                "-t", str(seg_dur), "-c:v", "libx264", "-preset", "fast",
                "-pix_fmt", "yuv420p", "-c:a", "aac", out_file,
            ], capture_output=True, check=False)
        else:
            # Retime the [rec_start, rec_start+available] window to exactly
            # seg_dur so each visual segment matches its narration window.
            speed = available / seg_dur if seg_dur > 0 else 1.0
            subprocess.run([
                FFMPEG, "-y", "-ss", str(rec_start), "-t", str(available),
                "-i", recording_path, "-filter:v", f"setpts=PTS/{speed:.6f}",
                "-an", "-c:v", "libx264", "-preset", "fast",
                "-pix_fmt", "yuv420p", out_file,
            ], capture_output=True, check=False)

        seg_files.append({"file": out_file, "start": seg["start"],
                          "duration": seg["duration"]})

    return {"segments": seg_files, "recording_duration": rec_dur,
            "total_narration_duration": total_duration}


# ═══════════════════════════════════════════════════════════════════════════════
# Step 4: HyperFrames composition (aspect + fit aware)
# ═══════════════════════════════════════════════════════════════════════════════

def parse_aspect(aspect: str):
    if aspect in ASPECTS:
        return ASPECTS[aspect]
    m = re.match(r"^(\d+)[x:](\d+)$", aspect)
    if m:
        return int(m.group(1)), int(m.group(2))
    raise ValueError(f"Unsupported --aspect '{aspect}' (use 9:16, 1:1, 16:9, or WxH)")


def geometry_for(w: int, h: int, fit: str):
    """Return (screen_css, caption_bottom) for the given frame and fit mode.

    contain     letterbox the recording inside a 16:9-shaped band (portrait) or
                the full frame (landscape). Nothing is cropped.
    cover       scale the recording to fill the frame, cropping overflow.
    cover-pan   like cover, plus a slow pan so the crop travels across the shot.
    """
    cover = fit in ("cover", "cover-pan")
    if cover:
        screen = {"top": 0, "left": 0, "width": w, "height": h, "radius": 0,
                  "object_fit": "cover"}
        return screen, 90

    if w / h >= 1.6:
        # Landscape frame: a 16:9-ish recording already fills it; captions overlay.
        screen = {"top": 0, "left": 0, "width": w, "height": h, "radius": 0,
                  "object_fit": "contain"}
        return screen, 80

    # Portrait / square: 16:9 band at top, captions in the space below.
    band_h = int((w - 80) * 9 / 16)
    screen = {"top": 60, "left": 40, "width": w - 80, "height": band_h,
              "radius": 24, "object_fit": "contain"}
    return screen, 120


def build_composition(voiceover_path: str, timing_data: list, segments: list,
                      total_dur: float, title: str, out_dir: str,
                      aspect: str = "9:16", fit: str = "contain") -> str:
    os.makedirs(os.path.join(out_dir, "assets"), exist_ok=True)

    import shutil
    shutil.copy(voiceover_path, os.path.join(out_dir, "assets", "voiceover.wav"))
    for seg in segments:
        shutil.copy(seg["file"], os.path.join(out_dir, "assets", os.path.basename(seg["file"])))
    with open(os.path.join(out_dir, "assets", "timing.json"), "w") as f:
        json.dump(timing_data, f, indent=2)

    w, h = parse_aspect(aspect)
    screen, caption_bottom = geometry_for(w, h, fit)
    comp_dur = round(total_dur + 0.5, 2)
    n = len(timing_data)
    window = 6  # max simultaneously visible caption words

    # caption font scales with frame width (tuned for 1080px wide)
    caption_size = max(30, int(54 * w / 1080))

    video_html = "\n    ".join(
        f'<video class="screen-video" src="assets/{os.path.basename(s["file"])}" '
        f'muted playsinline data-start="{s["start"]}" '
        f'data-duration="{s["duration"]}" id="screen-seg-{i}"></video>'
        for i, s in enumerate(segments)
    )

    word_spans = "\n        ".join(
        f'<span class="cw" id="cw-{i}">{wd["word"]}</span>'
        for i, wd in enumerate(timing_data)
    )

    # ---- GSAP timeline: rolling captions + optional cover-pan ----
    lines = ["const tl = gsap.timeline({ paused: true });"]
    if fit == "cover-pan":
        lines.append(
            'tl.fromTo(".screen-video", { objectPosition: "0% 50%" }, '
            '{ objectPosition: "100% 50%", duration: ' + str(comp_dur) +
            ', ease: "none" }, 0);'
        )
    for i, wd in enumerate(timing_data):
        s = wd["start"]; e = wd["end"]
        lines.append(f'tl.set("#cw-{i}", {{ display: "inline-block" }}, {s});')
        lines.append(f'tl.set("#cw-{i}", {{ color: "var(--accent)" }}, {s});')
        lines.append(f'tl.set("#cw-{i}", {{ color: "var(--caption-text)" }}, {round(e, 3)});')
        hide = timing_data[i + window]["start"] if i + window < n else min(round(e + 0.4, 3), comp_dur)
        lines.append(f'tl.set("#cw-{i}", {{ display: "none" }}, {round(hide, 3)});')
    lines.append('window.__timelines["main"] = tl;')
    timeline_js = "\n    ".join(lines)

    html = f'''<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width={w}, height={h}" />
  <title>{title}</title>
  <script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
  <style>
    :root {{
      --bg: #0b0b10;
      --surface: #14141c;
      --accent: #ffd23f;
      --text: #f5f5f0;
      --text-muted: #9a9aa6;
      --caption-text: #f5f5f0;
      --border: rgba(255,255,255,0.08);
    }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: Inter, system-ui, -apple-system, "Segoe UI", sans-serif;
      -webkit-font-smoothing: antialiased;
    }}
    #root {{
      position: relative;
      width: {w}px;
      height: {h}px;
      overflow: hidden;
      background:
        radial-gradient(1200px 600px at 50% -100px, rgba(255,210,63,0.10), transparent 70%),
        linear-gradient(180deg, #0b0b10 0%, #101018 100%);
    }}
    .screen-video {{
      position: absolute;
      top: {screen["top"]}px;
      left: {screen["left"]}px;
      width: {screen["width"]}px;
      height: {screen["height"]}px;
      border-radius: {screen["radius"]}px;
      object-fit: {screen["object_fit"]};
      background: var(--surface);
      border: 1px solid var(--border);
      z-index: 5;
    }}
    .caption-container {{
      position: absolute;
      bottom: {caption_bottom}px;
      left: 60px;
      right: 60px;
      min-height: 190px;
      display: flex;
      align-items: flex-end;
      justify-content: center;
      z-index: 20;
    }}
    .caption-line {{
      display: flex;
      flex-wrap: wrap;
      justify-content: center;
      align-items: center;
      gap: 14px;
      max-width: {int(w * 0.9)}px;
      text-align: center;
      background: rgba(11,11,16,0.72);
      backdrop-filter: blur(10px);
      -webkit-backdrop-filter: blur(10px);
      border-radius: 20px;
      padding: 22px 32px;
    }}
    .cw {{
      display: none;
      font-size: {caption_size}px;
      font-weight: 700;
      letter-spacing: -0.02em;
      line-height: 1.25;
      color: var(--caption-text);
    }}
  </style>
</head>
<body>
  <div id="root" data-composition-id="main" data-width="{w}" data-height="{h}"
       data-duration="{comp_dur}">

    {video_html}

    <div class="caption-container" id="caption-overlay">
      <div class="caption-line">
        {word_spans}
      </div>
    </div>

    <audio id="voiceover" src="assets/voiceover.wav" data-start="0"
           data-duration="{total_dur}" data-volume="1"></audio>
  </div>

  <script>
    {timeline_js}
  </script>
</body>
</html>'''

    out_path = os.path.join(out_dir, "index.html")
    with open(out_path, "w") as f:
        f.write(html)
    return out_path


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    p = argparse.ArgumentParser(description="Vertical Shorts Pipeline")
    p.add_argument("--script", required=True, help="Caption text (and narration text unless --narration is given)")
    p.add_argument("--narration", default=None, help="Voiceover text when it differs from captions (e.g. Vietnamese)")
    p.add_argument("--recording", required=True)
    p.add_argument("--output-dir", default="./output")
    p.add_argument("--voice", default=None, help="Kokoro voice (af_heart) or edge-tts ShortName (vi-VN-HoaiMyNeural)")
    p.add_argument("--voice-lang", default="en", help="TTS + Whisper language code (en, vi, ...)")
    p.add_argument("--tts-engine", default="kokoro", choices=["kokoro", "edge"])
    p.add_argument("--speed", type=float, default=1.0)
    p.add_argument("--title", default="Tech Short")
    p.add_argument("--aspect", default="9:16", help="9:16 | 1:1 | 16:9 | WxH")
    p.add_argument("--fit", default="contain", choices=FITS, help="contain | cover | cover-pan")
    p.add_argument("--skip-tts", action="store_true")
    p.add_argument("--skip-timing", action="store_true")
    p.add_argument("--skip-align", action="store_true")
    args = p.parse_args()

    # Default voice per engine
    voice = args.voice
    if not voice:
        if args.tts_engine == "edge":
            voice = EDGE_DEFAULT_VOICE.get(args.voice_lang.split("-")[0], "en-US-AriaNeural")
        else:
            voice = "af_heart"

    with open(args.script, encoding="utf-8") as f:
        script_text = f.read().strip()

    narration_text = script_text
    if args.narration:
        with open(args.narration, encoding="utf-8") as f:
            narration_text = f.read().strip()

    os.makedirs(args.output_dir, exist_ok=True)

    vo_path = os.path.join(args.output_dir, "voiceover.wav")
    timing_path = os.path.join(args.output_dir, "timing.json")
    seg_dir = os.path.join(args.output_dir, "recording_segments")

    # Step 1 — voiceover (narration language)
    if args.skip_tts:
        print("⏭️  Skipping TTS")
        import soundfile as sf
        info = sf.info(vo_path)
        vo_meta = {"path": vo_path, "duration_s": info.duration,
                   "sample_rate": info.samplerate, "voice": voice,
                   "engine": args.tts_engine}
    else:
        print(f"🎤 TTS ({args.tts_engine}/{voice}/{args.voice_lang})...")
        vo_meta = generate_voiceover(narration_text, vo_path, voice, args.speed,
                                     args.tts_engine, args.voice_lang)
        print(f"   ✅ {vo_meta['duration_s']}s")

    # Step 2 — caption timing (caption language mapped onto narration audio)
    if args.skip_timing:
        print("⏭️  Skipping timing")
        with open(timing_path) as f:
            timing_data = json.load(f)
    else:
        print("⏱️  Word timing...")
        timing_data = extract_word_timings(vo_path, script_text, timing_path,
                                           lang=args.voice_lang.split("-")[0],
                                           narration_text=narration_text)
        print(f"   ✅ {len(timing_data)} words")

    # Step 3 — align recording
    if args.skip_align:
        print("⏭️  Skipping alignment")
        timing_segs = group_timing_into_segments(timing_data)
        seg_files = []
        for fname in sorted(os.listdir(seg_dir)):
            if fname.startswith("seg_") and fname.endswith(".mp4"):
                idx = int(fname.replace("seg_", "").replace(".mp4", ""))
                s = timing_segs[idx] if idx < len(timing_segs) else \
                    {"start": idx * 3, "duration": 3}
                seg_files.append({
                    "file": os.path.join(seg_dir, fname),
                    "start": s["start"], "duration": s["duration"],
                })
        seg_meta = {"segments": seg_files}
    else:
        print("🎬 Aligning recording...")
        seg_meta = align_recording(args.recording, timing_data, seg_dir,
                                   vo_meta["duration_s"])
        print(f"   ✅ {len(seg_meta['segments'])} segments")

    # Step 4 — composition
    print("🖼️  Composition...")
    comp_dir = os.path.join(args.output_dir, "hyperframes")
    comp_path = build_composition(vo_path, timing_data, seg_meta["segments"],
                                  vo_meta["duration_s"], args.title, comp_dir,
                                  aspect=args.aspect, fit=args.fit)

    config = {
        "title": args.title, "voice": voice, "engine": args.tts_engine,
        "voice_lang": args.voice_lang, "aspect": args.aspect, "fit": args.fit,
        "duration_s": vo_meta["duration_s"], "word_count": len(timing_data),
        "segment_count": len(seg_meta["segments"]),
        "composition_path": comp_path,
    }
    with open(os.path.join(args.output_dir, "render_config.json"), "w") as f:
        json.dump(config, f, indent=2)

    print(f"\n✅ Done! {vo_meta['duration_s']}s, {len(timing_data)} words")
    print(f"   → {comp_path}")
    print(f"\nNext: cd {comp_dir} && npx hyperframes check && npx hyperframes render")


if __name__ == "__main__":
    main()
