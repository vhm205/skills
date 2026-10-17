#!/usr/bin/env python3
"""
Full Recut & Motion Compositing Pipeline
Handles:
1. Seamless segment extraction with 30ms audio crossfades
2. Lossless concat to base video
3. Watermark removal (Gemini / AI logos via resolution-aware delogo)
4. Subtitle rendering BEHIND motion graphics
5. Multi-layer HyperFrames overlay compositing (ProRes 4444 alpha .mov and full-screen .mp4)
6. Social audio normalization (-14 LUFS, -1 dBTP)
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

DEFAULT_SUB_STYLE = (
    "FontName=Helvetica,FontSize=18,Bold=1,"
    "PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BackColour=&H00000000,"
    "BorderStyle=1,Outline=2,Shadow=0,"
    "Alignment=2,MarginV=85"
)

def get_dimensions(video_path: Path):
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height",
        "-of", "json",
        str(video_path)
    ]
    res = subprocess.check_output(cmd)
    data = json.loads(res)
    stream = data["streams"][0]
    return int(stream["width"]), int(stream["height"])

def run_pipeline(edl_path: Path, output_path: Path, remove_watermark: bool = True, watermark_preset: str = "gemini"):
    with open(edl_path, "r", encoding="utf-8") as f:
        edl = json.load(f)

    project_dir = edl_path.parent
    sources = edl.get("sources", {})
    ranges = edl.get("ranges", [])
    overlays = edl.get("overlays", [])
    subtitles_file = edl.get("subtitles")

    clips_dir = project_dir / "clips_graded"
    clips_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("STEP 1: Extracting segments with 30ms audio crossfades...")
    print("=" * 60)
    segment_paths = []
    
    first_src = Path(list(sources.values())[0]) if sources else None
    vw, vh = (720, 1280)
    if first_src and first_src.exists():
        vw, vh = get_dimensions(first_src)

    for i, r in enumerate(ranges):
        src_key = r["source"]
        src_file = sources[src_key]
        start = float(r["start"])
        end = float(r["end"])
        dur = end - start
        out_seg = clips_dir / f"seg_{i:02d}.mp4"

        fade_out_st = max(0.0, dur - 0.03)
        af = f"afade=t=in:st=0:d=0.03,afade=t=out:st={fade_out_st:.3f}:d=0.03"

        cmd = [
            "ffmpeg", "-y",
            "-ss", f"{start:.3f}",
            "-to", f"{end:.3f}",
            "-i", str(src_file),
            "-vf", f"scale={vw}:{vh}",
            "-af", af,
            "-c:v", "libx264", "-preset", "fast", "-crf", "19",
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
            str(out_seg)
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        segment_paths.append(out_seg)
        quote = r.get("quote", "")[:35]
        print(f"  Segment {i:02d}: {dur:5.2f}s | {src_key} [{start:.2f}s - {end:.2f}s] {quote}...")

    print("\n" + "=" * 60)
    print("STEP 2: Lossless concatenation to base.mp4...")
    print("=" * 60)
    concat_list = project_dir / "_concat.txt"
    concat_list.write_text("".join(f"file '{p.resolve()}'\n" for p in segment_paths))

    base_mp4 = project_dir / "base.mp4"
    cmd_concat = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", str(concat_list),
        "-c", "copy",
        "-movflags", "+faststart",
        str(base_mp4)
    ]
    subprocess.run(cmd_concat, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    concat_list.unlink(missing_ok=True)

    probe_out = subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(base_mp4)
    ])
    base_dur = float(json.loads(probe_out)["format"]["duration"])
    print(f"  Base video assembled: {base_mp4} ({base_dur:.2f}s)")

    print("\n" + "=" * 60)
    print("STEP 3: Compositing Subtitles BEHIND Graphic Overlays...")
    print("=" * 60)

    inputs = ["-i", str(base_mp4)]
    for ov in overlays:
        inputs += ["-i", str(ov["file"])]

    filter_parts = []
    
    # 3.1: Base video filter chain (Delogo if requested -> Subtitles)
    base_v_filters = []
    if remove_watermark:
        # Scale coordinates to video resolution
        scale_x = vw / 720.0
        scale_y = vh / 1280.0
        dx = int(round(566 * scale_x))
        dy = int(round(1130 * scale_y))
        dw = int(round(68 * scale_x))
        dh = int(round(75 * scale_y))
        base_v_filters.append(f"delogo=x={dx}:y={dy}:w={dw}:h={dh}")
        print(f"  [Filter] Watermark delogo enabled at x={dx}, y={dy}, w={dw}, h={dh}")

    if subtitles_file and Path(subtitles_file).exists():
        subs_path = str(Path(subtitles_file).resolve()).replace(":", r"\:").replace("'", r"\'")
        sub_style = edl.get("subtitle_style", DEFAULT_SUB_STYLE)
        base_v_filters.append(f"subtitles='{subs_path}':force_style='{sub_style}'")
        print(f"  [Filter] Subtitles layer placed behind graphic overlays")

    if base_v_filters:
        filter_parts.append(f"[0:v]{','.join(base_v_filters)}[subv]")
        current_layer = "[subv]"
    else:
        current_layer = "[0:v]"

    # 3.2: PTS shifts and overlay chain
    for idx, ov in enumerate(overlays, start=1):
        t = float(ov["start_in_output"])
        filter_parts.append(f"[{idx}:v]setpts=PTS-STARTPTS+{t}/TB[a{idx}]")

    for idx, ov in enumerate(overlays, start=1):
        t = float(ov["start_in_output"])
        dur = float(ov["duration"])
        end = t + dur
        next_label = f"[v{idx}]"
        filter_parts.append(
            f"{current_layer}[a{idx}]overlay=enable='between(t,{t:.3f},{end:.3f})'{next_label}"
        )
        current_layer = next_label

    filter_str = ";".join(filter_parts)

    raw_composite = project_dir / "preview_raw.mp4"
    cmd_composite = [
        "ffmpeg", "-y"
    ] + inputs + [
        "-filter_complex", filter_str,
        "-map", current_layer,
        "-map", "0:a",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-c:a", "copy",
        str(raw_composite)
    ]

    t0 = time.time()
    subprocess.run(cmd_composite, check=True)
    print(f"  Composite rendered successfully in {time.time()-t0:.1f}s")

    print("\n" + "=" * 60)
    print("STEP 4: Social Loudness Normalization (-14 LUFS, -1 dBTP)...")
    print("=" * 60)
    cmd_norm = [
        "ffmpeg", "-y",
        "-i", str(raw_composite),
        "-c:v", "copy",
        "-af", "loudnorm=I=-14:TP=-1:LRA=11",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
        "-movflags", "+faststart",
        str(output_path)
    ]
    subprocess.run(cmd_norm, check=True)
    if raw_composite.exists():
        raw_composite.unlink()

    print(f"\nFinal export ready at: {output_path}")

def main():
    parser = argparse.ArgumentParser(description="Talking-Head Video Recut & Compositing Pipeline")
    parser.add_argument("--edl", default="edit/edl.json", help="Path to edit decision list (EDL)")
    parser.add_argument("-o", "--output", default="edit/final.mp4", help="Output path for final video")
    parser.add_argument("--no-delogo", action="store_true", help="Disable watermark removal")
    args = parser.parse_args()

    edl_p = Path(args.edl)
    if not edl_p.exists():
        print(f"Error: EDL file not found at {edl_p}")
        sys.exit(1)

    out_p = Path(args.output)
    out_p.parent.mkdir(parents=True, exist_ok=True)

    run_pipeline(
        edl_path=edl_p,
        output_path=out_p,
        remove_watermark=not args.no_delogo
    )

if __name__ == "__main__":
    main()
