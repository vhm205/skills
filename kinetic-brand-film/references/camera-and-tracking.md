# Dynamic Camera Rigging & Caption Tracking (`caption-camera-follow`)

The `caption-camera-follow` pattern turns a static screen composition into a dynamic, cinematographic sequence where a virtual camera whips, zooms, and tracks between active subjects, badges, and spoken lyrics.

---

## 1. The Core Architecture

Instead of moving individual elements across the screen, wrap the entire multi-element scene inside a **Dedicated Camera Rig**:

```html
<!-- Virtual Camera Rig Container -->
<div 
  id="camera-rig-scene" 
  data-layout-allow-overflow="true" 
  style="position: absolute; inset: 0; width: 100%; height: 100%; transform-origin: 50% 50%; opacity: 0; z-index: 18; pointer-events: none;"
>
  <!-- Focal Zone Left: Hero Subject / Portrait -->
  <div id="subject-anchor-left" style="position: absolute; top: 180px; left: 160px; width: 480px;">
    <!-- Portrait Card with Safe Aspect Ratio -->
    <div class="cinematic-frame" style="width: 100%; height: 520px;">
      <img src="team_photo.jpg" alt="Lead" style="width: 100%; height: 100%; object-fit: cover; object-position: center 25%;">
    </div>
    <!-- Focal Caption 1 -->
    <div id="follow-chant-1" style="margin-top: 24px; opacity: 0;">
      <div class="neon-badge-blue">MISSION FIRST</div>
    </div>
  </div>

  <!-- Focal Zone Right: Core Value / Secondary Subject -->
  <div id="subject-anchor-right" style="position: absolute; top: 220px; right: 160px; width: 540px;">
    <!-- Focal Caption 2 -->
    <div id="follow-chant-2" style="opacity: 0;">
      <div class="neon-badge-mint">BUILDING LIVE</div>
    </div>
  </div>

  <!-- Focal Zone Center: Final Punchline / Impact Statement -->
  <div id="follow-chant-punch" style="position: absolute; bottom: 140px; left: 50%; transform: translateX(-50%); width: 900px; text-align: center; opacity: 0;">
    <div style="font-size: 54px; font-weight: 900; letter-spacing: -0.02em; color: #ffffff;">
      GIẢI PHÁP BỨT PHÁ MỌI GIỚI HẠN.
    </div>
  </div>
</div>
```

---

## 2. The 3-Step Camera Choreography

A high-energy rap chant or musical bar usually has a 3-part cadence: **Call 1 -> Call 2 -> Climax Punch**.

### Step 1: Lock onto Zone 1 (Left Anchor)
The camera punches in slightly (`scale: 1.06`) and pans rightwards (`x: +28px`) to center the left subject on the canvas:

```javascript
// Fade in Rig
tl.fromTo(
  "#camera-rig-scene",
  { opacity: 0, scale: 1.0, x: 0, y: 0 },
  { opacity: 1, duration: 0.2, ease: "power2.out", immediateRender: false },
  59.45
);

// Vocal Beat 1 (59.66s)
addBeatFlash(59.7, 0.4);
addCameraShake(59.7, 6);
tl.fromTo(
  "#follow-chant-1",
  { scale: 1.8, opacity: 0 },
  { scale: 1.0, opacity: 1, duration: 0.18, ease: "back.out(1.8)", immediateRender: false },
  59.66
);
tl.to(
  "#camera-rig-scene",
  { scale: 1.06, x: 28, y: -6, duration: 0.28, ease: "power2.out" },
  59.66
);
```

### Step 2: Whip-Track across to Zone 2 (Right Anchor)
On the second call, dim Zone 1 to keep visual focus crisp, reveal Zone 2 with a scale slam, and whip the camera leftwards (`x: -32px`):

```javascript
// Vocal Beat 2 (60.44s)
addBeatFlash(60.5, 0.45);
addCameraShake(60.5, 7);
tl.to("#follow-chant-1", { opacity: 0.2, scale: 0.95, duration: 0.15 }, 60.44);

tl.fromTo(
  "#follow-chant-2",
  { scale: 1.8, opacity: 0 },
  { scale: 1.0, opacity: 1, duration: 0.18, ease: "back.out(1.8)", immediateRender: false },
  60.44
);
tl.to(
  "#camera-rig-scene",
  { scale: 1.10, x: -32, y: -4, duration: 0.32, ease: "power3.out" },
  60.44
);
```

### Step 3: Recenter & Dolly-In Climax Punch
The camera recenters (`x: 0, y: 0`) and pushes deeply forward (`scale: 1.14`) during the spoken punchline:

```javascript
// Vocal Climax (60.90s)
tl.to(["#follow-chant-1", "#follow-chant-2"], { opacity: 0, duration: 0.2 }, 60.9);

tl.fromTo(
  "#follow-chant-punch",
  { opacity: 0, y: 25, scale: 0.9 },
  { opacity: 1, y: 0, scale: 1.0, duration: 0.25, ease: "back.out(1.5)", immediateRender: false },
  60.9
);
tl.to(
  "#camera-rig-scene",
  { scale: 1.14, x: 0, y: 0, duration: 1.3, ease: "sine.inOut" },
  60.9
);

// Rapid Cut into Next Scene (62.30s)
tl.to(
  ["#camera-rig-scene", "#follow-chant-punch"],
  { opacity: 0, scale: 1.18, duration: 0.2, ease: "power2.in" },
  62.3
);
```

---

## 3. Safe-Framing Coordinates Table

When setting `scale` and `(x, y)` translations, observe these bounds to prevent subjects and typography from being clipped by the 1920x1080 viewport:

| Camera State | Recommended Scale | Max Horizontal Offset (X) | Max Vertical Offset (Y) | Purpose |
| :--- | :--- | :--- | :--- | :--- |
| **Neutral Overview** | `1.00` | `0px` | `0px` | Scene entrance & context |
| **Zone Push (Left/Right)** | `1.05 - 1.08` | `±25px` to `±35px` | `±5px` to `±10px` | Isolating one speaker/card |
| **Hard Focus (Tight)** | `1.10 - 1.14` | `±40px` | `±12px` | High-emphasis keyword punch |
| **Climax Punch (Center)** | `1.14 - 1.18` | `0px` | `0px` | Fullscreen punchline / statement |
| **Exit Blow-Up** | `1.18 - 1.25` | `0px` | `0px` | Quick zoom transition into cut |
