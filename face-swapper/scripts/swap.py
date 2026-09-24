#!/usr/bin/env python3
"""
Face Swapper CLI using InsightFace and Inswapper (inswapper_128.onnx).
Supports swapping target video or image with one or more source face images.
"""

import argparse
import os
import sys
import subprocess
from pathlib import Path
import cv2
import numpy as np

VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.mkv', '.webm', '.flv', '.m4v'}
IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.webp', '.bmp', '.tiff'}

def find_model_path():
    candidates = [
        os.path.expanduser('~/.insightface/models/inswapper_128.onnx'),
        os.path.expanduser('~/.cache/huggingface/hub/models--ezioruan--inswapper_128.onnx/snapshots/6ffdf0e83c5996cc425e77b59913fc48d79441be/inswapper_128.onnx'),
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    # Search ~/.insightface or ~/.cache
    for root, _, files in os.walk(os.path.expanduser('~/.insightface')):
        if 'inswapper_128.onnx' in files:
            return os.path.join(root, 'inswapper_128.onnx')
    raise FileNotFoundError("Could not locate inswapper_128.onnx. Please ensure it is placed in ~/.insightface/models/")

def get_face(app, img, name="image"):
    faces = app.get(img)
    if not faces:
        raise ValueError(f"No face detected in {name}")
    # Return face with largest bounding box
    return max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))

def process_image(app, swapper, target_path, face_data, out_dir):
    target_img = cv2.imread(str(target_path))
    if target_img is None:
        raise ValueError(f"Could not read target image: {target_path}")

    target_face = get_face(app, target_img, str(target_path))
    target_stem = target_path.stem
    target_ext = target_path.suffix if target_path.suffix.lower() in IMAGE_EXTENSIONS else '.png'

    results = []
    for face_stem, face_obj in face_data:
        out_name = f"{target_stem}_{face_stem}{target_ext}"
        out_path = os.path.join(out_dir, out_name)
        res = swapper.get(target_img.copy(), target_face, face_obj, paste_back=True)
        cv2.imwrite(out_path, res)
        results.append(out_path)
        print(f"[Done] Image saved: {out_path}")
    return results

def process_video(app, swapper, target_path, face_data, out_dir, crf=18, preset='fast'):
    cap = cv2.VideoCapture(str(target_path))
    if not cap.isOpened():
        raise ValueError(f"Could not open target video: {target_path}")

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0 or np.isnan(fps):
        fps = 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    target_stem = target_path.stem

    print(f"Video Info: {width}x{height} @ {fps:.2f} fps, {total_frames} total frames")

    # Prepare ffmpeg subprocesses for each face
    procs = []
    out_paths = []
    for face_stem, _ in face_data:
        out_file = os.path.join(out_dir, f"{target_stem}_{face_stem}.mp4")
        out_paths.append(out_file)
        cmd = [
            'ffmpeg', '-y',
            '-f', 'rawvideo',
            '-vcodec', 'rawvideo',
            '-s', f"{width}x{height}",
            '-pix_fmt', 'bgr24',
            '-r', str(fps),
            '-i', '-',
            '-i', str(target_path),
            '-map', '0:v:0',
            '-map', '1:a?',
            '-c:v', 'libx264',
            '-pix_fmt', 'yuv420p',
            '-crf', str(crf),
            '-preset', preset,
            '-c:a', 'copy',
            out_file
        ]
        p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
        procs.append(p)

    frame_idx = 0
    detected_count = 0
    last_target_face = None

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            frame_idx += 1

            faces = app.get(frame)
            if faces:
                target_face = max(faces, key=lambda f: (f.bbox[2]-f.bbox[0]) * (f.bbox[3]-f.bbox[1]))
                last_target_face = target_face
                detected_count += 1
            else:
                target_face = last_target_face

            for i, (_, face_obj) in enumerate(face_data):
                if target_face is not None:
                    res_frame = swapper.get(frame.copy(), target_face, face_obj, paste_back=True)
                else:
                    res_frame = frame
                procs[i].stdin.write(res_frame.tobytes())

            if frame_idx % 30 == 0 or (total_frames > 0 and frame_idx == total_frames):
                pct = f"({frame_idx/total_frames*100:.1f}%)" if total_frames > 0 else ""
                print(f"Processed frame {frame_idx}/{total_frames} {pct} - detected in {detected_count} frames")

    finally:
        cap.release()
        for p in procs:
            if p.stdin:
                p.stdin.close()
            p.wait()

    print(f"[Done] Video processing complete for {len(face_data)} faces across {frame_idx} frames.")
    for p in out_paths:
        size_mb = os.path.getsize(p) / (1024 * 1024)
        print(f"  -> {p} ({size_mb:.2f} MB)")
    return out_paths

def main():
    parser = argparse.ArgumentParser(description="Inswapper Face Swap CLI")
    parser.add_argument("--target", "-t", required=True, help="Target video or image file path")
    parser.add_argument("--faces", "-f", nargs="+", required=True, help="One or more source face image paths")
    parser.add_argument("--output-dir", "-o", default="face-swap", help="Output directory (default: face-swap)")
    parser.add_argument("--crf", type=int, default=18, help="Video CRF (default: 18)")
    parser.add_argument("--preset", default="fast", help="x264 preset (default: fast)")
    parser.add_argument("--model", help="Path to inswapper_128.onnx")

    args = parser.parse_args()

    target_path = Path(args.target).expanduser().resolve()
    if not target_path.exists():
        sys.exit(f"Error: Target path does not exist: {target_path}")

    face_paths = [Path(f).expanduser().resolve() for f in args.faces]
    for fp in face_paths:
        if not fp.exists():
            sys.exit(f"Error: Face image does not exist: {fp}")

    out_dir = Path(args.output_dir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    model_path = args.model or find_model_path()
    print(f"Using inswapper model: {model_path}")

    import insightface
    from insightface.app import FaceAnalysis

    print("Initializing face analyzer...")
    app = FaceAnalysis(name='buffalo_l', providers=['CoreMLExecutionProvider', 'CPUExecutionProvider'])
    app.prepare(ctx_id=0, det_size=(640, 640))

    print("Loading Inswapper ONNX model...")
    swapper = insightface.model_zoo.get_model(model_path, download=False, preview=False)

    print("Extracting source face embeddings...")
    face_data = []
    for fp in face_paths:
        img = cv2.imread(str(fp))
        if img is None:
            sys.exit(f"Error reading source face image: {fp}")
        face_obj = get_face(app, img, name=fp.name)
        face_data.append((fp.stem, face_obj))
        print(f"  Loaded source face: {fp.name}")

    ext = target_path.suffix.lower()
    if ext in VIDEO_EXTENSIONS:
        print(f"\nProcessing target video: {target_path}")
        process_video(app, swapper, target_path, face_data, str(out_dir), crf=args.crf, preset=args.preset)
    elif ext in IMAGE_EXTENSIONS:
        print(f"\nProcessing target image: {target_path}")
        process_image(app, swapper, target_path, face_data, str(out_dir))
    else:
        sys.exit(f"Unsupported file format: {ext}")

if __name__ == "__main__":
    main()
