# Rules & Fatal Pitfalls Guide

This document captures mission-critical lessons, edge-case bugs, and engineering guardrails learned during the production of high-tempo kinetic video compositions.

---

## 1. The Nesting Trap (Unclosed DIVs & Black Screen Gaps)

### The Bug
In complex scenes with multiple nested containers (e.g. camera tracking rigs, tilt wrappers, cards), a missing or misplaced `</div>` causes subsequent elements to become unintentional children of an earlier container:

```html
<!-- INCORRECT: Notice the unclosed camera rig wrapping the next section -->
<div id="camera-rig-scene5">
  <div id="follow-chant-1">...</div>
  <!-- Missing </div> here! -->

  <div id="build-view-crescendo">
    <!-- Crescendo is trapped inside the camera rig! -->
  </div>
</div>
```

When GSAP fades out `#camera-rig-scene5` at `62.3s`:
```javascript
tl.to("#camera-rig-scene5", { opacity: 0, duration: 0.2 }, 62.3);
```
**Result**: The entire `#build-view-crescendo` disappears along with its parent rig, causing a **dead black screen** between `62.3s` and `64.0s` even though GSAP is trying to animate the crescendo!

### The Strict Rule
1. **Sibling Hierarchy**: All distinct sub-beats or sequential views inside a `<section class="clip">` MUST be direct sibling `<div>`s, never nested inside each other.
2. **Close Rigs Immediately**: The closing tag of a camera rig must appear immediately after its tracked elements.
3. **Audit Before Render**: Inspect the DOM indentation or grep tag pairs whenever a section renders blank.

---

## 2. GSAP `immediateRender: false` on Delayed `fromTo` Tweens

### The Bug
By default, GSAP `fromTo()` executes the `from` variables **immediately** at time `t = 0` when the timeline is built, not when the playhead reaches the specified start time.

If an element has `opacity: 0` in inline styles or starts offscreen, an un-flagged `fromTo()` at `t = 59.5s` might prematurely set its position or interfere with earlier layout computations.

### The Strict Rule
Always set `immediateRender: false` on ANY `fromTo()` tween that occurs after `0.0s`:

```javascript
// CORRECT
tl.fromTo(
  "#my-delayed-element",
  { opacity: 0, scale: 1.6 },
  { opacity: 1, scale: 1.0, duration: 0.25, ease: "back.out(1.6)", immediateRender: false }, // <-- CRITICAL
  59.5
);
```

---

## 3. Face-Safe Framing for Portrait & Team Photography

### The Problem
Using arbitrary 16:9 full-width covers (`object-fit: cover` with default `center center`) on founder portraits or team photography almost always crops off either:
- The top of the head/hairline, OR
- The subject's chin and chest.

Furthermore, dynamic UI elements (HUD badges, kinetic captions) placed on top of faces make the video look amateurish and obscure the human subjects.

### The Rules for Team Assets
1. **Use Explicit Aspect-Ratio Containers**: Never place a portrait directly on the 16:9 canvas without a frame. Place it inside a dedicated card (`width: 480px; height: 520px;` or `aspect-ratio: 3/4` / `4/5`).
2. **Top-Weighted Object Position**:
   ```css
   object-fit: cover;
   object-position: center 25%; /* Keeps head and eyes in upper third */
   ```
3. **Dedicated HUD Anchors**: Place badges, labels, and camcorder timecodes in the corners or outside the card frame, never floating directly over faces.

---

## 4. Exact Audio Duration Locking

### The Problem
- If HyperFrames `<div class="composition" data-duration="78.5">` is set to `77.0s`, the render engine stops 1.5s early, violently truncating the music outro.
- If it is set to `80.0s`, the video sits on a silent, frozen black frame for 1.5s after the audio track has ended.

### The Rule
Always inspect the audio file's exact duration to the second decimal place using `ffprobe`:
```bash
ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 audio.mp3
# Example output: 78.524000
```
Then lock your composition container to that exact duration:
```html
<div class="composition" data-duration="78.5">
```

---

## 5. The Verification Protocol (0 Black Screens, 0 Linter Errors)

Before running a full, time-consuming final video render:

1. **Static Validation**:
   ```bash
   npx hyperframes check
   ```
   Ensure **0 errors** (all data-start + data-duration attributes valid, tracks properly closed, tags balanced).

2. **Time-Slice Snapshot Audit**:
   Take snapshot frames at:
   - The end of every scene transition (e.g. `6.9s`, `17.9s`, `31.9s`, `47.9s`, `63.9s`).
   - The peak of the pre-drop build (e.g. `63.5s`).
   - The climax drop (e.g. `64.2s`).
   ```bash
   npx hyperframes snapshot --at 63.5 -o snapshot_63.5.png
   ```

3. **Verify Element Visibility**:
   Inspect the snapshot image. If any frame displays an empty background without intended typography or graphics, immediately inspect tag closures and GSAP timeline start/end times.
