# Kinetic Motion & Typography Pattern Library

This reference provides production-tested HTML, CSS, and GSAP implementation patterns for high-energy tech brand films and music-synced videos.

---

## 1. Syllable-Level Kinetic Slam (`caption-kinetic-slam`)

Used for fast rap bars, hard vocal chops, and manifesto taglines where words or syllables slam into view on individual beats.

### HTML Structure
```html
<!-- Fullscreen Centered HUD Container -->
<div id="kinetic-slam-layer" style="position: absolute; inset: 0; display: flex; flex-direction: column; justify-content: center; align-items: center; z-index: 35; pointer-events: none; opacity: 0;">
  <!-- Cyber Glass HUD Box -->
  <div id="kinetic-box" style="display: flex; flex-direction: column; align-items: center; background: rgba(8, 12, 18, 0.92); border: 1.5px solid rgba(56, 189, 248, 0.5); border-radius: 24px; padding: 24px 54px; box-shadow: 0 0 60px rgba(0, 0, 0, 0.9), 0 0 35px rgba(56, 189, 248, 0.25); backdrop-filter: blur(16px);">
    <!-- Protocol Header Tag -->
    <div class="hud-tag font-mono" style="font-size: 13px; color: #38bdf8; margin-bottom: 12px; letter-spacing: 0.25em;">
      [ PROTOCOL SYNC // VOCAL FLOW ]
    </div>
    <!-- Syllable/Letter Slam Line -->
    <div style="display: flex; align-items: center; gap: 16px; line-height: 1;">
      <span id="slam-word-1" class="font-mono" style="font-size: 110px; font-weight: 900; color: #ffffff; text-shadow: 0 0 30px rgba(255, 255, 255, 0.8); display: inline-block;">A</span>
      <span class="status-dot-blue" style="width: 14px; height: 14px; border-radius: 50%; background: #38bdf8; box-shadow: 0 0 12px #38bdf8;"></span>
      <span id="slam-word-2" class="font-mono" style="font-size: 110px; font-weight: 900; color: #10a37f; text-shadow: 0 0 35px rgba(16, 163, 127, 0.9); display: inline-block;">I</span>
    </div>
    <!-- Subtitle changing on beat -->
    <div id="slam-subtitle" class="font-mono" style="font-size: 15px; color: #cbd5e1; margin-top: 14px; letter-spacing: 0.2em; text-transform: uppercase;">
      AUTONOMOUS INTELLIGENCE
    </div>
  </div>
</div>
```

### GSAP Timeline Choreography
```javascript
// Enter HUD container slightly before first syllable
tl.fromTo(
  "#kinetic-slam-layer",
  { opacity: 0, scale: 0.82 },
  { opacity: 1, scale: 1.0, duration: 0.18, ease: "back.out(1.5)", immediateRender: false },
  29.45
);

// Syllable 1 (29.50s) - Hard punch in
addCameraShake(29.5, 4);
tl.fromTo(
  "#slam-word-1",
  { scale: 1.85, opacity: 0 },
  { scale: 1.0, opacity: 1, duration: 0.14, ease: "back.out(1.7)", immediateRender: false },
  29.5
);
tl.set("#slam-word-2", { opacity: 0.25, scale: 0.9 }, 29.5);

// Syllable 2 (29.70s) - Second hit + optical flash
addBeatFlash(29.7, 0.3);
addCameraShake(29.7, 4);
tl.fromTo(
  "#slam-word-2",
  { scale: 1.85, opacity: 0 },
  { scale: 1.0, opacity: 1, duration: 0.14, ease: "back.out(1.7)", immediateRender: false },
  29.7
);

// CRITICAL: Rapid Exit as rap vocal cuts off
tl.to("#kinetic-slam-layer", { opacity: 0, scale: 1.1, duration: 0.08, ease: "power2.in" }, 30.76);
```

---

## 2. Multi-Directional Kinetic Words (Impact Snare Hits)

Words slam into the frame from three distinct vector axes (Left, Right, Bottom) on consecutive snare or vocal hits.

### HTML Structure
```html
<div style="position: absolute; inset: 0; pointer-events: none; z-index: 25;">
  <!-- Word from Left -->
  <div id="word-slam-left" style="position: absolute; top: 380px; left: 160px; font-size: 78px; font-weight: 900; color: #ffffff; letter-spacing: -0.02em; text-shadow: 0 0 35px rgba(56,189,248,0.5); opacity: 0;">
    CODE THẬT.
  </div>
  <!-- Word from Right -->
  <div id="word-slam-right" style="position: absolute; top: 480px; right: 160px; font-size: 78px; font-weight: 900; color: #10a37f; letter-spacing: -0.02em; text-shadow: 0 0 35px rgba(16,163,127,0.5); opacity: 0;">
    AGENTS THẬT.
  </div>
  <!-- Word from Bottom -->
  <div id="word-slam-bottom" style="position: absolute; top: 580px; left: 50%; transform: translateX(-50%); font-size: 84px; font-weight: 900; color: #f59e0b; letter-spacing: -0.02em; text-shadow: 0 0 40px rgba(245,158,11,0.6); opacity: 0;">
    TỰ ĐỘNG HÓA.
  </div>
</div>
```

### GSAP Timeline Choreography
```javascript
// Hit 1: Left Vector (57.0s)
tl.fromTo(
  "#word-slam-left",
  { x: -240, opacity: 0, scale: 1.2 },
  { x: 0, opacity: 1, scale: 1.0, duration: 0.25, ease: "back.out(1.6)", immediateRender: false },
  57.0
);
addBeatFlash(57.0, 0.25);

// Hit 2: Right Vector (57.8s)
tl.fromTo(
  "#word-slam-right",
  { x: 240, opacity: 0, scale: 1.2 },
  { x: 0, opacity: 1, scale: 1.0, duration: 0.25, ease: "back.out(1.6)", immediateRender: false },
  57.8
);
addBeatFlash(57.8, 0.25);

// Hit 3: Center Bottom Anchor (58.6s)
tl.fromTo(
  "#word-slam-bottom",
  { y: 80, opacity: 0, scale: 1.2 },
  { y: 0, opacity: 1, scale: 1.0, duration: 0.25, ease: "back.out(1.6)", immediateRender: false },
  58.6
);
addBeatFlash(58.6, 0.35);
addCameraShake(58.6, 5);

// Clear words before next scene section
tl.to(["#word-slam-left", "#word-slam-right", "#word-slam-bottom"], { opacity: 0, duration: 0.18 }, 59.4);
```

---

## 3. Pre-Drop Hyper Crescendo (Climax Escalation)

Rapid-fire, accelerating typography stacking right before a major drop. Each word appears with escalating scale, brightness, and screen shake.

### HTML Structure
```html
<div id="build-view-crescendo" style="position: absolute; inset: 0; display: flex; flex-direction: column; justify-content: center; align-items: center; z-index: 28; pointer-events: none; opacity: 0;">
  <div style="display: flex; flex-direction: column; align-items: center; gap: 20px;">
    <!-- Step 1 Word -->
    <div id="crescendo-w1" style="font-size: 72px; font-weight: 900; letter-spacing: -0.02em; color: #ffffff; text-shadow: 0 0 35px rgba(255,255,255,0.4); opacity: 0;">
      KHÔNG CẦN CHỜ ĐỢI
    </div>
    <!-- Step 2 Word (Color Shift) -->
    <div id="crescendo-w2" style="font-size: 80px; font-weight: 900; letter-spacing: -0.02em; color: #38bdf8; text-shadow: 0 0 45px rgba(56,189,248,0.7); opacity: 0;">
      KHÔNG THIẾU TỰ TIN
    </div>
    <!-- Step 3 Word (Massive Punch) -->
    <div id="crescendo-w3" style="font-size: 96px; font-weight: 900; letter-spacing: -0.02em; color: #10a37f; text-shadow: 0 0 60px rgba(16,163,127,0.85); opacity: 0;">
      TRIỂN KHAI NGAY HÔM NAY.
    </div>
  </div>
</div>
```

### GSAP Timeline Choreography
```javascript
// Reveal Crescendo Container
tl.fromTo(
  "#build-view-crescendo",
  { opacity: 0 },
  { opacity: 1, duration: 0.15, ease: "power2.out", immediateRender: false },
  62.35
);

// Escalation 1 (62.45s)
addBeatFlash(62.45, 0.3);
tl.fromTo(
  "#crescendo-w1",
  { opacity: 0, scale: 1.5 },
  { opacity: 1, scale: 1.0, duration: 0.2, ease: "back.out(1.6)", immediateRender: false },
  62.45
);

// Escalation 2 (63.00s)
addBeatFlash(63.0, 0.38);
tl.fromTo(
  "#crescendo-w2",
  { opacity: 0, scale: 1.5 },
  { opacity: 1, scale: 1.0, duration: 0.2, ease: "back.out(1.6)", immediateRender: false },
  63.0
);

// Escalation 3 Climax (63.50s) - Pre-Drop Peak
addBeatFlash(63.5, 0.55);
addCameraShake(63.5, 7);
tl.fromTo(
  "#crescendo-w3",
  { opacity: 0, scale: 1.6 },
  { opacity: 1, scale: 1.0, duration: 0.2, ease: "back.out(1.8)", immediateRender: false },
  63.5
);

// Glitch Out 0.15s before the drop hits
tl.fromTo("#glitch-overlay", { opacity: 0 }, { opacity: 0.85, duration: 0.1 }, 63.85);
tl.to("#build-view-crescendo", { opacity: 0, scale: 1.15, duration: 0.15, ease: "power2.in" }, 63.85);

// The Drop Hits at 64.0s
addBeatFlash(64.0, 0.8);
addCameraShake(64.0, 12);
```

---

## 4. Laser Slash Strike-Through (Anti-Bureaucracy Cut)

An angled laser strike slicing through outdated buzzwords (e.g. "SLIDE DECK", "REPORTS").

### CSS
```css
.laser-slash {
  position: absolute;
  height: 6px;
  background: linear-gradient(90deg, transparent, #ef4444 20%, #ffffff 50%, #ef4444 80%, transparent);
  box-shadow: 0 0 15px #ef4444, 0 0 35px #ef4444;
  border-radius: 3px;
  transform-origin: left center;
  pointer-events: none;
}
```

### GSAP Animation
```javascript
// Slice across in 0.18s on snare drop
tl.fromTo(
  "#laser-slash-1",
  { scaleX: 0 },
  { scaleX: 1, duration: 0.18, ease: "power4.out", immediateRender: false },
  0.85
);
addBeatFlash(0.85, 0.35);
```

---

## 5. Matrix Repeat Wallpaper (Ambient Scrolling Code/Manifesto)

A low-opacity, high-tech background ticker streaming across multiple rows in alternating directions.

### CSS
```css
.matrix-repeat-bg {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  justify-content: space-around;
  opacity: 0.12;
  pointer-events: none;
  overflow: hidden;
}
.matrix-row {
  display: flex;
  white-space: nowrap;
  gap: 40px;
  font-family: "Roboto Mono", monospace;
  font-size: 32px;
  font-weight: 800;
  letter-spacing: 0.15em;
  color: #64748b;
  text-transform: uppercase;
}
```

### GSAP Continuous Drift
```javascript
tl.fromTo("#matrix-row-1", { x: 0 }, { x: -350, duration: 12.0, ease: "none" }, startTime);
tl.fromTo("#matrix-row-2", { x: -280 }, { x: 80, duration: 12.0, ease: "none" }, startTime);
tl.fromTo("#matrix-row-3", { x: 0 }, { x: -300, duration: 12.0, ease: "none" }, startTime);
```
