---
name: faceless-video
description: Produce reviewed faceless explainers with HyperFrames.
version: 0.1.0
author: Minh Vu, Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [video, explainer, hyperframes, voice-clone, vietnamese]
    related_skills: [faceless-explainer, hyperframes, media-use, claude-code]
---

# Faceless Video Production

Own the editorial, research, voice, synchronization, review, and QA pipeline for a short faceless explainer. Delegate all visual design and implementation to the existing `/faceless-explainer` HyperFrames skill; never duplicate its typography, diagram, graphics, data-visualization, composition, or motion rules.

## When to Use

Use when the user asks for `/faceless-video` or wants a complete short explainer from a topic, audience, duration, voice reference, article, notes, or source material.

Do not use for a website/product promo, a talking-head recut, plain captions on existing footage, an unnarrated motion graphic, or a long-form video. Route those through `/hyperframes`.

## Required Skill Loading

Before production:

1. Load `/hyperframes` because it is the mandatory video entry point.
2. Load `/faceless-explainer` as the visual owner.
3. Load `/media-use` before sourcing or generating audio or external media.
4. Load `/claude-code` when Claude Opus is the production route.
5. Load HyperFrames domain skills only when `/faceless-explainer` asks for them.

The wrapper's approved teaching structure and content contract replace HyperFrames' editorial discretion. HyperFrames may refine visual execution but must not rewrite the approved meaning, claims, narration, or subtitle meaning.

## Defaults and Override Merge

Start with this immutable default object, then apply only explicit user overrides. Unmentioned values remain unchanged.

```yaml
video:
  type: faceless_explainer
  duration: 45-60s
  platform: [TikTok, Instagram Reels, YouTube Shorts]
  aspect_ratio: 9:16
  resolution: 1080x1920
content:
  narration_language: Vietnamese
  subtitle_language: English
visual:
  style: editorial_technology
  stock_footage: false
  talking_head: false
  generic_ai_robot_imagery: false
voice:
  engine: OmniVoice
  mode: voice_clone
models:
  editorial: GPT-5.6 Sol
  production: Claude Opus
hyperframes:
  skill: /faceless-explainer
```

Normalize platform and aspect ratio only when implied unambiguously: Shorts/Reels/TikTok defaults to `9:16` and `1080x1920`; YouTube landscape means `16:9` and `1920x1080`; square means `1:1` and `1080x1080`. Preserve any explicitly requested resolution.

## Workspace and Durable State

Use `videos/<topic-slug>/` unless the user gives another project directory. Persist this layout:

```text
<project>/
├── input/
├── editorial/
│   ├── input-analysis.json
│   ├── asset-plan.json
│   ├── research.md
│   ├── teaching-structure.md
│   └── script.json
├── assets/
├── audio/
├── production/
│   ├── state.json
│   ├── timing.json
│   ├── subtitles.json
│   └── hyperframes/
├── preview/
└── output/
    └── final.mp4
```

Copy or reference user inputs without altering originals. Store source provenance in the editorial files. Use `<SKILL_DIR>/scripts/state.py` to initialize, transition, approve gates, and lock approved artifacts. Never infer progress from chat alone when `production/state.json` exists.

Canonical states:

```text
input_analysis -> asset_planning -> researching? -> building_structure
-> structure_review -> writing_script -> script_review
-> building_hyperframes -> visual_verification -> generating_voice
-> syncing_timeline -> syncing_subtitles -> qa -> video_review
-> revising -> video_review -> completed
```

`researching` is skipped when the research skip rule applies. `revising` may route to any affected production stage, then returns through affected QA to `video_review`.

## Model Routing

### Editorial route

Use the active GPT-5.6 Sol session for input analysis, source analysis, research, factual verification, teaching design, Vietnamese narration copy, and English subtitle copy. If the active model is not GPT-5.6 Sol, select an available GPT-5.6 Sol route or tell the user that the configured editorial model is unavailable before substituting a weaker model.

### Production route

Use Claude Opus for HyperFrames implementation, visual reasoning, diagram construction, animation, visual verification, audio integration, timing, subtitles, QA, and render revisions. Prefer Claude Code print mode with `--model opus`, a bounded turn count, and the project as `workdir`; use interactive mode only for a genuinely iterative production session. Confirm the returned model usage identifies an Opus model when structured output provides it.

Do not silently fall back to a cheaper/weaker production model. If Opus is unavailable, pause as an external dependency blocker unless the user explicitly authorizes another model. User-requested model overrides always win.

## Exactly Three Human Review Gates

The normal workflow has exactly these gates:

1. Teaching structure
2. Final script
3. Rendered video

Do not add approval questions for research, asset planning, visual style, storyboard sketches, voice generation, captions, timing, or internal QA. Interrupt elsewhere only when essential information cannot be derived safely or an external dependency blocks execution.

Run HyperFrames in its autonomous production mode so its internal storyboard/sketch checkpoints do not create extra user gates. Treat wrapper approval of `teaching-structure.md` and `script.json` as the locked editorial decision. HyperFrames' final-look checkpoint is satisfied only by this wrapper's rendered-video gate.

## Procedure

### 1. Analyze Input

Extract and persist:

- topic, audience, requested duration
- platform, aspect ratio, and resolution
- voice reference and any transcript
- source/reference materials and visual assets
- explicit overrides
- supplied script, article, notes, research, documentation, or other complete explanation

Apply defaults plus overrides and write `editorial/input-analysis.json`. Essential inputs are topic, audience, target duration, and voice reference only when voice cloning is requested. Ask for a missing essential input in one concise batch; otherwise continue.

Research skip rule: when a supplied script, article, notes, or source package sufficiently contains the required explanation, use it as primary truth and skip general research. Perform only targeted verification needed for accuracy or requested by the user.

Completion criterion: every field is recorded, every override is explicit, and the research decision has a reason.

### 2. Plan Sources and Assets

Write `editorial/asset-plan.json` with three lists:

1. `supplied`
2. `agent_generated_or_derived`
3. `user_would_materially_improve_accuracy`

Also list required factual sources and planned visual evidence. HyperFrames can generate typography, diagrams, flows, charts from supported data, abstract graphics, kinetic type, and conceptual systems; do not request external assets when those are sufficient. Do not block for optional assets. Ask only when a necessary external visual cannot be generated reliably and omission would make the explanation inaccurate.

Completion criterion: each need has an owner, source, necessity level, and target scene or claim.

### 3. Research When Needed

When research is not skipped, use `web_search` and `web_extract`, prioritizing official documentation, primary papers, authoritative datasets, and direct technical sources. Gather only enough to:

- explain the topic accurately
- identify concepts, misconceptions, audience relevance, and exclusions
- verify important claims
- support any numerical or comparative statement

Write concise findings and URLs to `editorial/research.md`. Distinguish sourced facts from editorial interpretation. Never invent chart numbers.

Completion criterion: every material claim planned for the short has a supplied or researched source, or is labeled clearly as analogy/opinion.

### 4. Build Teaching Structure

Create approximately 5–7 scenes for a 45–60 second short. Define teaching angle, core takeaway, hook, viewer misconception/question, teaching spine, scene purpose, facts, visual intent, and final takeaway. Use one primary teaching point per scene. Put the main idea near the beginning, remove side information, and end on one memorable sentence.

Identify appropriate diagrams, flows, comparisons, graphs, state transitions, and timelines, but do not implement them. Persist the full structure in `editorial/teaching-structure.md`.

#### Gate 1: Teaching Structure

Transition to `structure_review` and show only:

- teaching angle
- hook
- scene sequence
- core takeaway
- final takeaway

Ask for approval or revision. On revision, update with GPT-5.6 Sol and return to the same gate. On approval, record gate approval and lock `teaching-structure.md`.

### 5. Generate the Content Contract

For every approved scene write this exact schema to `editorial/script.json`:

```json
{
  "scene_id": "",
  "purpose": "",
  "voice_vi": "",
  "subtitle_en": "",
  "visual_intent": "",
  "facts": [],
  "estimated_duration": 0
}
```

The file may contain top-level metadata plus a `scenes` array. Vietnamese narration must be natural, conversational, concise, technically accurate, TTS-friendly, and optimized for listening. English subtitles must preserve meaning in natural concise English and be easy to split into mobile cues. Visual intent states what viewers should understand, not low-level HTML or motion implementation.

Check estimated total duration against the requested range using realistic spoken pacing; estimates guide review only and never override actual generated audio timing.

#### Gate 2: Final Script

Transition to `script_review` and show:

- hook
- full Vietnamese narration
- English subtitle copy
- scene order
- estimated total duration

Ask for approval or revision. On revision, update with GPT-5.6 Sol and return to the same gate. On approval, record approval and lock both the teaching structure and script. Later stages may not change narration meaning, factual claims, or subtitle meaning without explicit user instruction.

### 6. Hand Off Visual Production to HyperFrames

Create the HyperFrames project under `production/hyperframes/` and invoke `/faceless-explainer` in autonomous production mode. Pass:

- locked teaching structure and script
- asset plan and supplied assets
- source/reference materials and provenance
- platform, aspect ratio, resolution, and visual direction
- explicit instruction that approved content is immutable

Map wrapper scenes one-to-one to HyperFrames frame/scene identifiers where practical and persist the mapping. HyperFrames alone owns typography, diagrams, abstract graphics, data visualization, composition, and motion implementation. Do not recreate those instructions in this skill.

Completion criterion: HyperFrames has a playable assembled project, every wrapper scene maps to an implementation scene, and no approved content changed.

### 7. Mandatory Visual Verification

Before any user preview, route Claude Opus through every generated scene. Check and automatically fix:

- diagram nodes, arrows, order, labels, hierarchy, cause/effect, and I/O
- data values, labels, axes, magnitudes, comparison direction, and source consistency
- terminology, spelling, capitalization, hierarchy, duplication, truncation
- abstract graphics for misleading implications
- narration/visual/fact alignment and cross-scene consistency
- animation reveal order
- mobile safe areas, text size, subtitle reserve, and diagram legibility

Use HyperFrames lint/check/snapshot/contact-sheet or equivalent `/faceless-explainer` verification. Review rendered frames, not code alone. Repeat until no material correctness issue remains. Never expose an unverified preview.

### 8. Generate Voice

Use the configured engine; default to OmniVoice local voice cloning. Feed the locked narration exactly, voice reference audio, and reference transcript when available. Generate one file per scene under `audio/scene_NN.wav`. Create/cache reusable clone state when the engine supports it, without modifying the user's source audio.

If the user selected another engine such as VieNeu-TTS v3, use that engine and preserve all other defaults. If the configured engine or required model is unavailable, surface the dependency blocker; do not silently switch engines.

Completion criterion: every narrated scene has a non-empty readable audio file generated from the exact approved text.

### 9. Measure and Synchronize Audio

Use `ffprobe` or `ffmpeg` to measure actual files programmatically. Write `production/timing.json` with each scene's audio duration, timeline start, and timeline end. Use cumulative measured audio as the source of truth; include any explicit transition/breathing allowance as separately named fields rather than hiding it in audio duration.

Have Claude Opus + HyperFrames synchronize scene lengths, animation beats, diagram reveals, highlights, and transitions to actual narration. Never cut narration. Do not reveal the full explanation before the corresponding words.

Completion criterion: timing totals recompute exactly from measured files plus explicit allowances, and HyperFrames scene boundaries match the timing map.

### 10. Synchronize English Subtitles

Split the locked English copy into short timed cues based on the relevant Vietnamese narration and actual scene timing. Keep approximately two lines maximum, mobile-safe positioning, readable duration, and no important visual overlap. Persist `production/subtitles.json` and integrate captions directly into HyperFrames; the user never creates or imports SRT files.

Completion criterion: every approved subtitle meaning is represented once, cue times are monotonic and non-overlapping, and cues fit inside their scene windows.

### 11. Mandatory Automated QA

Run content, visual, audio, subtitle, animation, and technical QA before preview.

- Content: exact approved narration, sourced facts, equivalent subtitle meaning, no unsupported claims.
- Visual: inspect all text, diagrams, graphics, charts, labels, arrows, connections, and sequences.
- Audio: all files present, intelligible, unclipped, non-empty, and duration map verified against files.
- Subtitles: complete, readable, safe, correct English, correctly timed, no critical overlap.
- Animation: correct explanation order, sufficient hold times, non-distracting transitions.
- Technical: aspect ratio, resolution, asset resolution, overflow, missing resources, lint/check/render errors.

Automatically fix production defects, rerun affected checks, and render test frames when needed. Verify locked artifacts still match their hashes after QA.

Completion criterion: all required checks pass or any documented non-material warning has visual evidence showing it is harmless.

### 12. Render Preview and Gate Video

Render `preview/preview.mp4`, then verify the file exists and use `ffprobe` to read total duration and stream metadata. Show only:

- the preview video
- total duration
- scene count

Transition to `video_review`. Do not show implementation logs unless user action is required.

#### Gate 3: Rendered Video

Accept approval or targeted feedback. Route feedback by owner:

- content/meaning/claims: GPT-5.6 Sol, reopening the script lock only with explicit instruction
- visual/diagram/motion: Claude Opus + `/faceless-explainer`
- voice: configured TTS engine
- timing/subtitle/render: Claude Opus + local tools

Modify only affected scenes/components where possible. Rerun affected QA plus lock verification, render a new preview, and return to this gate until approved.

### 13. Final Render

After Gate 3 approval, render `output/final.mp4` at requested resolution and high quality. Verify with `ffprobe` that video and audio streams exist, resolution/aspect match, duration is plausible, and the file is non-empty. Persist the project and transition to `completed`.

Final response includes the final video path, total duration, scene count, narration/subtitle languages, and project path.

## Pitfalls

- Do not run general research when complete supplied material is enough.
- Do not ask the user for a storyboard, script, subtitles, diagrams, asset list, timing map, SRT, or HyperFrames details.
- Do not let HyperFrames independently rewrite approved editorial content.
- Do not count HyperFrames autonomous summaries or internal checks as extra approval gates.
- Do not use estimated durations after real audio exists.
- Do not fabricate numerical charts or visual relationships.
- Do not inspect only source code; mandatory visual verification requires rendered frames.
- Do not expose a preview before visual verification and QA.
- Do not claim model routing, voice generation, or render success without tool output.

## Verification Checklist

- [ ] Defaults merged with only explicit overrides
- [ ] Research skip decision persisted
- [ ] Asset/source plan persisted without unnecessary user requests
- [ ] Teaching structure approved and locked
- [ ] Script approved and locked
- [ ] HyperFrames `/faceless-explainer` owns every visual implementation
- [ ] Production used approved model or user-authorized substitute
- [ ] Mandatory scene-by-scene visual verification completed
- [ ] Voice files measured and timing map recomputed
- [ ] English subtitles synchronized from approved meaning
- [ ] Full automated QA passed before preview
- [ ] Preview metadata verified before Gate 3
- [ ] Targeted revisions reran affected QA
- [ ] Final MP4 streams, dimensions, duration, and path verified
- [ ] Exactly three normal human review gates occurred
