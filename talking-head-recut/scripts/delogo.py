#!/usr/bin/env python3
"""
Automated Gemini & AI Watermark Removal Tool
Uses FFmpeg's delogo filter with smart resolution-aware scaling.
Seamlessly interpolates the corner logo area without visual degradation.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

# Base coordinates tuned on 720x1280 portrait video
GEMINI_WATERMARK_BASE_720x1280 = {
    "x": 566,
    "y": 1130,
    "w": 68,
    "h": 75
}

def get_video_dimensions(file_path: Path):
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height",
        "-of", "json",
        str(file_path)
    ]
    res = subprocess.check_output(cmd)
    data = json.loads(res)
    stream = data["streams"][0]
    return int(stream["width"]), int(stream["height"])

def compute_delogo_params(width: int, height: int, preset: str = "gemini"):
    if preset == "gemini":
        base_w, base_h = 720, 1280
        scale_x = width / base_w
        scale_y = height / base_h
        
        x = int(round(GEMINI_WATERMARK_BASE_720x1280["x"] * scale_x))
        y = int(round(GEMINI_WATERMARK_BASE_720x1280["y"] * scale_y))
        w = int(round(GEMINI_WATERMARK_BASE_720x1280["w"] * scale_x))
        h = int(round(GEMINI_WATERMARK_BASE_720x1280["h"] * scale_y))
        
        # Ensure box stays within bounds
        if x + w > width:
            w = width - x
        if y + h > height:
            h = height - y
            
        return x, y, w, h
    else:
        raise ValueError(f"Unknown preset {preset}")

def remove_watermark(input_path: Path, output_path: Path, x: int, y: int, w: int, h: int, crf: int = 18):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    delogo_filter = f"delogo=x={x}:y={y}:w={w}:h={h}"
    
    cmd = [
        "ffmpeg", "-y",
        "-i", str(input_path),
        "-vf", delogo_filter,
        "-c:v", "libx264", "-preset", "medium", "-crf", str(crf),
        "-c:a", "copy",
        "-movflags", "+faststart",
        str(output_path)
    ]
    print(f"Applying delogo filter: {delogo_filter} to {input_path.name}...")
    subprocess.run(cmd, check=True)
    print(f"Saved watermark-free video: {output_path}")

def generate_comparison_frames(input_path: Path, output_path: Path, x: int, y: int, w: int, h: int, timestamp: float = 5.0, out_dir: Path = Path("verify")):
    out_dir.mkdir(parents=True, exist_ok=True)
    # Crop around watermark area with 30px padding
    pad = 30
    cx = max(0, x - pad)
    cy = max(0, y - pad)
    cw = w + pad * 2
    ch = h + pad * 2
    
    before_png = out_dir / "delogo_before.png"
    after_png = out_dir / "delogo_after.png"
    
    crop_filter = f"crop={cw}:{ch}:{cx}:{cy}"
    
    # Before
    subprocess.run([
        "ffmpeg", "-y", "-ss", str(timestamp), "-i", str(input_path),
        "-vf", crop_filter, "-vframes", "1", str(before_png)
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    # After
    subprocess.run([
        "ffmpeg", "-y", "-ss", str(timestamp), "-i", str(output_path),
        "-vf", crop_filter, "-vframes", "1", str(after_png)
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    print(f"Verification frames saved to {before_png} and {after_png}")

def main():
    parser = argparse.ArgumentParser(description="Watermark Removal (Delogo) for Talking-Head Videos")
    parser.add_argument("input", help="Path to input video file")
    parser.add_argument("-o", "--output", help="Path to output video file (default: <input_stem>_clean.mp4)")
    parser.add_argument("--preset", default="gemini", choices=["gemini", "custom"], help="Watermark preset")
    parser.add_argument("-x", type=int, help="Custom X coordinate")
    parser.add_argument("-y", type=int, help="Custom Y coordinate")
    parser.add_argument("-w", "--width", type=int, help="Custom width")
    parser.add_argument("-H", "--height", type=int, help="Custom height")
    parser.add_argument("--verify", action="store_true", help="Dump before & after crop images for verification")
    parser.add_argument("--crf", type=int, default=18, help="H.264 CRF quality (default: 18)")
    args = parser.parse_args()

    inp = Path(args.input)
    if not inp.exists():
        print(f"Error: input file '{inp}' does not exist.")
        sys.exit(1)

    out = Path(args.output) if args.output else inp.parent / f"{inp.stem}_clean{inp.suffix}"
    
    vw, vh = get_video_dimensions(inp)
    print(f"Input video dimensions: {vw}x{vh}")

    if args.preset == "custom":
        if None in (args.x, args.y, args.width, args.height):
            print("Error: custom preset requires -x, -y, -w, -H parameters.")
            sys.exit(1)
        x, y, w, h = args.x, args.y, args.width, args.height
    else:
        x, y, w, h = compute_delogo_params(vw, vh, preset=args.preset)

    print(f"Delogo coordinates: x={x}, y={y}, w={w}, h={h}")
    remove_watermark(inp, out, x, y, w, h, crf=args.crf)

    if args.verify:
        generate_comparison_frames(inp, out, x, y, w, h)

if __name__ == "__main__":
    main()
