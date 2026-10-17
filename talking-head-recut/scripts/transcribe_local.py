#!/usr/bin/env python3
"""
Local Whisper Word-Level Transcriber (No External APIs / Zero ElevenLabs)
Uses mlx-whisper (Apple Silicon optimized) or falls back to faster-whisper/whisper.
Generates word-level timestamps JSON and consolidated markdown review files.
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

def extract_audio(video_path: Path, audio_path: Path):
    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
        str(audio_path)
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def transcribe_clip(audio_path: Path, model_name: str, language: str = None):
    try:
        import mlx_whisper
        kwargs = {
            "path_or_hf_repo": model_name,
            "word_timestamps": True,
            "verbose": False
        }
        if language:
            kwargs["language"] = language
        result = mlx_whisper.transcribe(str(audio_path), **kwargs)
        return result
    except ImportError:
        pass

    try:
        from faster_whisper import WhisperModel
        model = WhisperModel("large-v3", device="auto", compute_type="float16")
        segments, info = model.transcribe(str(audio_path), word_timestamps=True, language=language)
        seg_list = []
        for s in segments:
            words = [{"word": w.word, "start": w.start, "end": w.end, "probability": w.probability} for w in s.words] if s.words else []
            seg_list.append({
                "id": s.id,
                "start": s.start,
                "end": s.end,
                "text": s.text,
                "words": words
            })
        return {"text": " ".join(s["text"] for s in seg_list), "segments": seg_list, "language": info.language}
    except ImportError:
        import whisper
        model = whisper.load_model("base")
        return model.transcribe(str(audio_path), word_timestamps=True, language=language)

def main():
    parser = argparse.ArgumentParser(description="Local Word-Level Whisper Transcriber")
    parser.add_argument("inputs", nargs="+", help="Input video or audio files/glob")
    parser.add_argument("--output-dir", default="edit/transcripts", help="Directory for transcript JSONs")
    parser.add_argument("--model", default="mlx-community/whisper-large-v3-turbo", help="Whisper model name/path")
    parser.add_argument("--language", default=None, help="Language code (e.g., 'vi', 'en')")
    parser.add_argument("--summary", default="edit/takes_packed.md", help="Markdown summary output path")
    args = parser.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    summary_path = Path(args.summary)
    summary_path.parent.mkdir(parents=True, exist_ok=True)

    input_files = []
    for inp in args.inputs:
        p = Path(inp)
        if p.is_dir():
            for ext in ("*.mp4", "*.mov", "*.m4a", "*.wav", "*.mp3"):
                input_files.extend(sorted(p.glob(ext)))
        elif p.is_file():
            input_files.append(p)
        else:
            for match in Path(".").glob(inp):
                if match.is_file():
                    input_files.append(match)

    input_files = sorted(list(set(input_files)))
    if not input_files:
        print(f"No input files found for {args.inputs}")
        sys.exit(1)

    print(f"Found {len(input_files)} file(s) to transcribe locally using {args.model}...")
    
    summary_lines = ["# Transcripts Summary & Take Review\n"]

    for idx, f in enumerate(input_files, 1):
        stem = f.stem
        out_json = out_dir / f"{stem}.json"
        
        if out_json.exists():
            print(f"[{idx}/{len(input_files)}] Using cached: {out_json}")
            with open(out_json, "r", encoding="utf-8") as jf:
                data = json.load(jf)
        else:
            print(f"[{idx}/{len(input_files)}] Transcribing: {f.name}")
            tmp_wav = out_dir / f"_{stem}.wav"
            try:
                extract_audio(f, tmp_wav)
                data = transcribe_clip(tmp_wav, model_name=args.model, language=args.language)
                with open(out_json, "w", encoding="utf-8") as jf:
                    json.dump(data, jf, ensure_ascii=False, indent=2)
            finally:
                if tmp_wav.exists():
                    tmp_wav.unlink()

        text = data.get("text", "").strip()
        segments = data.get("segments", [])
        dur = segments[-1]["end"] if segments else 0.0

        summary_lines.append(f"## {stem} ({f.name}) - Duration: {dur:.2f}s\n")
        summary_lines.append(f"**Full Text:** {text}\n")
        summary_lines.append("| Start | End | Segment Text |")
        summary_lines.append("|---|---|---|")
        for seg in segments:
            s_st = f"{seg.get('start', 0.0):.2f}"
            s_en = f"{seg.get('end', 0.0):.2f}"
            s_tx = seg.get('text', '').strip().replace('|', '-')
            summary_lines.append(f"| {s_st}s | {s_en}s | {s_tx} |")
        summary_lines.append("\n---\n")

    summary_path.write_text("\n".join(summary_lines), encoding="utf-8")
    print(f"\nDone! Transcripts saved to {out_dir}/, summary compiled to {summary_path}")

if __name__ == "__main__":
    main()
