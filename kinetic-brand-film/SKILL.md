---
name: kinetic-brand-film
description: Expert motion design and video director skill for creating high-energy, beat-synced tech brand films, startup manifestos, and product showcase videos using HyperFrames, GSAP, and Tailwind. Specializes in syllable-level kinetic slam typography, dynamic camera-follow tracking rigs, face-safe portrait framing, audio beat-sync triggers, and zero-black-screen visual continuity.
---

# Kinetic Brand Film & Manifesto Director

A specialized motion graphics and creative engineering director for producing high-voltage, music-synced tech brand films, startup manifestos, and kinetic showcase videos using **HyperFrames**, **GSAP**, and modern web rendering standards.

This skill is designed for scenarios where a company, team, or project wants to turn **static visual assets** (team photography, candid snapshots, UI screenshots, architecture diagrams) and an **energetic soundtrack** (rap, hip-hop, electronic, rock) into a film that moves with raw intensity and surgical beat precision.

---

## 1. Core Visual Philosophy: "Raw Builders, Zero Fluff"

- **No Stagnant Frames**: A static photo or screenshot should never sit still for more than 1.5 seconds without a parallax tilt, camera pan, or sync punch.
- **Syllable-Level Impact**: Hard rap vocals and rhythmic lyrics must have corresponding typographical slams (`caption-kinetic-slam`) that hit on the exact decisecond of the vocal attack and vanish cleanly when the bar closes.
- **Cinematic Framing Over Generic Covers**: Never splash a human portrait across a 16:9 canvas with naive `center center` cropping. Use framed cards (`3:4` or `4:5` ratio) with `object-position: center 25%` and camcorder/HUD telemetry overlays to preserve facial integrity and add documentary realism.
- **Continuous Ambient Energy**: Backgrounds must never be plain flat black. Layer subtle obsidian grids, slow-scrolling matrix code wallpapers, radial glows, and optical beat flashes to keep the frame feeling alive.

---

## 2. The 5-Phase Production Pipeline

```
[Phase 1: Audio Beat Grid] ──> [Phase 2: Track Architecture] ──> [Phase 3: Asset Staging]
                                                                        │
[Phase 5: QA & Final Render] <── [Phase 4: Kinetic Choreography] <──────┘
```

### Phase 1: Audio Beat Grid & Lyric Ingestion
1. **Determine Exact Duration**: Use `ffprobe` to find the exact audio length down to two decimals:
   ```bash
   ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 audio.mp3
   ```
2. **Map the Rhythm Grid**:
   - Identify tempo (BPM), primary snare hits, and 808 kick drops.
   - Transcribe lyrics phonetically and tag specific timestamps for rap syllables (e.g. `29.5s -> "A"`, `29.7s -> "I"`).
   - Locate the Pre-Drop Build section (typically 1.5s - 2.5s before the chorus drop) and the Main Drop.
3. Read the complete rhythm guide in [`references/beat-sync-guide.md`](references/beat-sync-guide.md).

### Phase 2: Track Architecture & Layout Guardrails
1. **HyperFrames Composition Root**:
   - Set `<div class="composition" data-duration="<EXACT_AUDIO_DURATION>">`.
   - Place `<audio src="audio.mp3">` at root level.
   - Insert global optical flash (`#flash-overlay`) and glitch (`#glitch-overlay`) overlays at root level.
2. **Sibling Hierarchy Discipline**:
   - Every sequential scene or sub-beat must be a **direct sibling** inside `<div class="track" data-track="main">`.
   - **NEVER nest later scene containers inside an earlier camera rig or fading card**. This is the #1 cause of blank screen bugs.
3. Read all critical guardrails in [`references/rules-and-pitfalls.md`](references/rules-and-pitfalls.md).

### Phase 3: Asset Staging & Portrait Safe-Zones
1. **Portrait Containers**:
   - Place team members inside `.cinematic-frame` cards (`aspect-ratio: 3/4` or `width: 480px; height: 520px;`).
   - Use `object-position: center 25%;` to ensure hair, eyes, and expressions are never cut off.
2. **Cyber HUD & Documentary Elements**:
   - Add `.camcorder-overlay` (`REC ● 24FPS`, live timecodes, lens crosshairs, telemetry stamps).
   - Add metallic status badges (`.metallic-badge` with glowing status dots).
   - Add background tickers (`.matrix-repeat-bg`) streaming brand phrases or terminal commands.

### Phase 4: Kinetic Choreography & Dynamic Rigging
1. **Typography Slams**:
   - **Kinetic Slam**: Centered glass HUD with letter/syllable hits (`back.out(1.6)`) and instant exit (`duration: 0.08` at vocal cutoff).
   - **Multi-Directional Words**: Impact words slamming simultaneously from Left, Right, and Bottom on snare intervals.
   - **Laser Slash**: Angled laser blade slicing through outdated paradigms on snare strikes.
   - **Pre-Drop Crescendo**: Escalating 3-word stack accelerating into the climax drop.
   - Code patterns available in [`references/motion-patterns.md`](references/motion-patterns.md).
2. **Dynamic Camera Rigging (`caption-camera-follow`)**:
   - Wrap multi-element scenes in a camera rig (`id="camera-rig-sceneX"`).
   - Whip and zoom between active vocal anchors (`scale: 1.06 -> 1.10 -> 1.14`, panning `x: ±30px` to keep focus tight).
   - Implementation guide in [`references/camera-and-tracking.md`](references/camera-and-tracking.md).
3. **GSAP Timeline Integrity**:
   - Always specify `immediateRender: false` on all delayed `fromTo()` animations.

### Phase 5: Verification, Snapshot Audit & Final Render
1. **Linter Check**:
   ```bash
   npx hyperframes check
   ```
   Must return **0 errors**.
2. **Time-Slice Snapshot Audit**:
   Take snapshot frames at:
   - Exact scene boundary transitions (e.g. `6.9s`, `17.9s`, `31.9s`, `59.4s`).
   - The pre-drop build peak and the drop slam.
   ```bash
   npx hyperframes snapshot --at 62.5 -o test_frame_62.5.png
   ```
   Inspect images to guarantee zero black frames, zero clipped text, and perfect alignment.
3. **Final Video Render**:
   ```bash
   npx hyperframes render -o renders/<project_name>_final.mp4
   ```

---

## 3. Reference Routing Table

| Topic | Reference Document | Key Concepts Covered |
| :--- | :--- | :--- |
| **Motion Patterns** | [`references/motion-patterns.md`](references/motion-patterns.md) | Kinetic Slam, Multi-Directional Words, Pre-Drop Crescendo, Laser Slash, Matrix Tickers. |
| **Camera Tracking** | [`references/camera-and-tracking.md`](references/camera-and-tracking.md) | `caption-camera-follow`, Coordinate bounds, Zone whipping, Climax punch dolly-in. |
| **Beat Synchronization** | [`references/beat-sync-guide.md`](references/beat-sync-guide.md) | `addBeatFlash`, `addCameraShake`, Decisecond syllable sync, Rapid Exit rule, Equalizer bars. |
| **Rules & Fatal Pitfalls** | [`references/rules-and-pitfalls.md`](references/rules-and-pitfalls.md) | The Nesting Trap, GSAP `immediateRender`, Face-safe cropping, Audio lock, Snapshot audits. |
| **Starter Template** | [`references/template-starter.html`](references/template-starter.html) | Production-ready boilerplate HTML + CSS + GSAP timeline scaffold. |

---

## 4. Quick-Start Command Sequence

When directed to build or upgrade a video project using this skill:

```bash
# 1. Inspect audio duration
ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 audio.mp3

# 2. Verify composition schema & timings
npx hyperframes check

# 3. Audit specific transition seconds
npx hyperframes snapshot --at 30.5 -o test_30.5.png

# 4. Render final output
npx hyperframes render -o renders/final_brand_film.mp4
```
