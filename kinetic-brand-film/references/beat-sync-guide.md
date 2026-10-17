# Beat-Sync & Audio Reactive Direction Guide

A kinetic brand film derives its energy from **synchronization with the rhythm track**. Every snare crack, bass kick, and rap bar must have an immediate visual consequence.

---

## 1. Global Setup: Optical Flash & Camera Shake Helpers

Place these overlays at the root level of your HTML (just inside `#root`):

```html
<!-- Optical Flash Overlay for Beat Hits -->
<div 
  id="flash-overlay" 
  style="position: absolute; inset: 0; background: #ffffff; opacity: 0; pointer-events: none; z-index: 90;" 
  data-layout-ignore="true"
></div>

<!-- Scanline & Glitch Overlays -->
<div 
  id="glitch-overlay" 
  style="position: absolute; inset: 0; background: rgba(56, 189, 248, 0.08); mix-blend-mode: screen; opacity: 0; pointer-events: none; z-index: 85;" 
  data-layout-ignore="true"
></div>
```

### GSAP Helper Functions
Define these at the start of your timeline script:

```javascript
// Helper for optical beat flashes on snares and drops
function addBeatFlash(time, opacity = 0.3) {
  tl.fromTo(
    "#flash-overlay",
    { opacity: opacity },
    { opacity: 0, duration: 0.22, ease: "power2.out", immediateRender: false },
    time
  );
}

// Camera shake helper for heavy beat drops and impacts
function addCameraShake(time, intensity = 6) {
  const shakeTl = gsap.timeline();
  shakeTl
    .to("#root", { x: intensity, y: -intensity, duration: 0.04, ease: "none" })
    .to("#root", { x: -intensity, y: intensity, duration: 0.04, ease: "none" })
    .to("#root", { x: intensity * 0.4, y: -intensity * 0.4, duration: 0.04, ease: "none" })
    .to("#root", { x: 0, y: 0, duration: 0.04, ease: "none" });
  tl.add(shakeTl, time);
}
```

---

## 2. Drum Hit Hierarchy & Visual Mapping

| Audio Event | Visual Impact | Shake Intensity | Flash Opacity | Example Timing Use |
| :--- | :--- | :--- | :--- | :--- |
| **Snare Hit** | Sharp typography micro-pulse or Directional Word slam | `2px - 4px` (or none) | `0.20 - 0.35` | Regular drum groove |
| **Kick Drum** | Card scale pump (`1.0 -> 1.02`), badge strobe | `3px - 5px` | `0.25 - 0.40` | Driving 4-on-the-floor / 808 |
| **Beat Drop / Crash** | Camera rig shockwave, UI explosion, color invert | `8px - 14px` | `0.65 - 0.85` | Major chorus / drop entrance |
| **Pre-Drop Build** | Accelerating strobe flash, pitch-riser scale up | Escalating `3 -> 7px` | Escalating `0.2 -> 0.55` | 1-2 seconds before climax |
| **Vocal Syllable** | Syllable-level Kinetic Slam (`back.out(1.6)`) | `3px - 5px` | `0.25 - 0.35` | Fast rap bars / chants |

---

## 3. Syllable Decisecond Alignment & The "Rapid Exit" Rule

### The Decisecond Alignment Rule
In fast hip-hop / rap tracks, human ears register lag at as little as **50ms (0.05s)**.
1. When mapping lyrics, locate the precise onset of each syllable using waveform tools or `ffprobe`.
2. Do not stagger words on generic whole seconds (e.g. `29.0s, 30.0s`). Use the exact vocal attack time (e.g. `29.50s, 29.70s, 30.00s`).

### The Rapid Exit Rule (Crucial for Rap Cadence)
Rap vocals stop sharply between bars. If a Kinetic Slam or Word Slam lingers on screen after the rapper has already finished the bar, the visual tempo feels dragging and sluggish.
- **Rule**: Terminate the typography layer **0.06s – 0.12s** after the final syllable ends.
- **GSAP Exit Recipe**:
```javascript
// Rap bar finishes at 30.70s -> Exit immediately at 30.76s:
tl.to("#kinetic-ai-slam-layer", { 
  opacity: 0, 
  scale: 1.10, 
  duration: 0.08, 
  ease: "power2.in" 
}, 30.76);
```

---

## 4. Audio-Reactive Equalizer Bars (Ambient Tech Detail)

Add a live simulated audio visualizer to product mockups or HUD headers to keep the frame feeling alive between major scene transitions:

```html
<div class="eq-visualizer" style="display: flex; align-items: flex-end; gap: 4px; height: 28px;">
  <div id="eq-bar-1" class="eq-bar" style="width: 4px; height: 12px; background: #38bdf8; border-radius: 2px;"></div>
  <div id="eq-bar-2" class="eq-bar" style="width: 4px; height: 18px; background: #38bdf8; border-radius: 2px;"></div>
  <div id="eq-bar-3" class="eq-bar" style="width: 4px; height: 8px; background: #38bdf8; border-radius: 2px;"></div>
  <div id="eq-bar-4" class="eq-bar" style="width: 4px; height: 22px; background: #10a37f; border-radius: 2px;"></div>
  <div id="eq-bar-5" class="eq-bar" style="width: 4px; height: 14px; background: #10a37f; border-radius: 2px;"></div>
</div>
```

```javascript
// Pseudo-random continuous wave animation
const eqBars = ["#eq-bar-1", "#eq-bar-2", "#eq-bar-3", "#eq-bar-4", "#eq-bar-5"];
for (let t = 0; t < totalDuration; t += 1.2) {
  tl.to(eqBars[0], { height: 8 + (t * 7) % 18, duration: 0.3, ease: "sine.inOut" }, t);
  tl.to(eqBars[1], { height: 10 + (t * 11) % 20, duration: 0.3, ease: "sine.inOut" }, t + 0.1);
  tl.to(eqBars[2], { height: 6 + (t * 13) % 16, duration: 0.3, ease: "sine.inOut" }, t + 0.2);
  tl.to(eqBars[3], { height: 12 + (t * 5) % 22, duration: 0.3, ease: "sine.inOut" }, t + 0.3);
  tl.to(eqBars[4], { height: 8 + (t * 9) % 18, duration: 0.3, ease: "sine.inOut" }, t + 0.4);
}
```
