---
name: face-swapper
description: |
  High-performance face swapper for videos and images using InsightFace and Inswapper (inswapper_128.onnx).
  Swaps the face in a target video or image with one or multiple source face images.
  Automatically extracts faces, handles video frame streaming with FFmpeg, preserves original audio,
  and outputs independent files per source face into face-swap/ or a specified directory.
license: MIT
metadata:
  version: "1.0.0"
---

# Face Swapper: Inswapper Video & Image Face Swapping

Use this skill whenever a user requests to swap faces in a target video or image using the Inswapper model with one or more source face images.

Example user prompts:
- `target video @fs-1.mov face image @hid/bn.png @hid/kk.png`
- `target image @photo.jpg face @person.png`
- `swap face of video @clip.mp4 with @face1.png @face2.png`

---

## Architecture & Capabilities

1. **Model Backbone**:
   - **Detection & Recognition**: InsightFace `buffalo_l` (RetinaFace `det_10g.onnx` + ArcFace `w600k_r50.onnx`).
   - **Face Swapper**: Inswapper 128 ONNX (`inswapper_128.onnx` located at `~/.insightface/models/inswapper_128.onnx`).
   - **Hardware Acceleration**: Automatically leverages `CoreMLExecutionProvider` on Apple Silicon with fallback to `CPUExecutionProvider`.

2. **Multi-Face Batching in Single Pass**:
   - For videos, face detection is performed **only once per frame**.
   - The detected face is swapped with all specified source face images concurrently and streamed directly into independent FFmpeg pipes.
   - Avoids redundant video decode/encode cycles.

3. **Audio & Quality Preservation**:
   - Retains original audio tracks without re-encoding (`-c:a copy`).
   - Encodes video using `H.264` (`libx264`, `yuv420p`, default CRF 18).

---

## Execution Guide

When triggered, identify:
1. **Target**: Path to target video (`.mp4`, `.mov`, `.webm`, `.avi`, `.mkv`) or image (`.png`, `.jpg`, `.jpeg`, `.webp`).
2. **Face Images**: One or multiple source face images (`.png`, `.jpg`, `.jpeg`, etc.).
3. **Output Directory**: Defaults to `face-swap/` in the current working directory, or custom path.

### CLI Command

Execute the bundled swap script using `uv`:

```bash
uv run --python 3.11 \
  --with insightface \
  --with onnxruntime \
  --with opencv-python \
  --with numpy \
  python ~/.gemini/config/skills/face-swapper/scripts/swap.py \
  --target "<TARGET_PATH>" \
  --faces "<FACE_1>" "<FACE_2>" ... \
  --output-dir "<OUTPUT_DIR>"
```

### CLI Arguments

| Argument | Flag | Description | Default |
| :--- | :--- | :--- | :--- |
| `--target` | `-t` | Path to target video or image | *(Required)* |
| `--faces` | `-f` | One or more source face image paths | *(Required)* |
| `--output-dir` | `-o` | Destination folder for outputs | `face-swap` |
| `--crf` | | H.264 constant rate factor (lower = higher quality) | `18` |
| `--preset` | | FFmpeg encoding speed preset (`ultrafast`, `fast`, `medium`) | `fast` |
| `--model` | | Custom path to `inswapper_128.onnx` | Auto-detected |

---

## Output Naming Convention

Outputs are saved independently per source face:

- **Target Video** (`example.mov`) + Faces (`alice.png`, `bob.png`):
  - `face-swap/example_alice.mp4`
  - `face-swap/example_bob.mp4`
- **Target Image** (`portrait.jpg`) + Faces (`alice.png`, `bob.png`):
  - `face-swap/portrait_alice.jpg`
  - `face-swap/portrait_bob.jpg`

---

## Verification Checklist

After running:
1. Verify each output file was created and is non-empty (`ls -lh <output_dir>`).
2. If video, verify playback format and stream parameters with `ffprobe`.
3. Provide clickable markdown links to the source files and generated output files for the user.
