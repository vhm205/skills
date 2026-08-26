---
name: openmontage-video-production
description: Produce governed videos with OpenMontage pipelines.
version: 0.1.0
author: Minh Vu, Hermes Agent
license: MIT
platforms: [windows, linux, macos]
metadata:
  hermes:
    tags: [video, production, openmontage, editing, captions, voiceover]
    related_skills: [hermes-agent]
---

# OpenMontage Video Production Skill

Use OpenMontage as a pipeline-driven production system for short explainers, screen demos, B-roll montages, talking-head edits, animations, and social clips. This skill orchestrates OpenMontage; it does not bypass its manifests, director skills, checkpoints, human approvals, or quality review.

## When to Use

- Use when the user asks to create, visualize, explain, edit, caption, narrate, or repurpose a video.
- Use for workflows such as screen recording + voiceover + captions, hook/B-roll/conclusion structures, and research-to-video explainers.
- Do not use for a single image, audio-only edit, or ordinary prose explanation unless a video deliverable is requested.

## Prerequisites

- OpenMontage checkout. Prefer `$OPENMONTAGE_HOME`; otherwise use the configured local checkout.
- Python 3.10+, Node.js 18+, FFmpeg. HyperFrames requires Node.js 22+ when selected.
- Optional provider keys belong in OpenMontage `.env`, never in Hermes config or chat. Zero-key mode uses Piper TTS, open footage/archive sources, Remotion, HyperFrames when available, and FFmpeg.

## How to Run

Use `terminal` from the OpenMontage checkout. On Windows, invoke commands through the shell-compatible `make`/Python/Node environment available on the machine.

```bash
cd "$OPENMONTAGE_HOME"
make setup
make preflight
```

For a production request, work through the OpenMontage project workspace and invoke the pipeline via the agent; do not write an ad-hoc API script.

## Quick Reference

```text
Pipeline candidates:
animated-explainer, screen-demo, cinematic, animation, hybrid,
talking-head, documentary-montage, clip-factory, podcast-repurpose,
avatar-spokesperson, localization-dub, character-animation

Core stages:
research -> proposal -> script -> scene_plan -> assets -> edit -> compose

Project output:
projects/<project-id>/renders/final.mp4
```

## Procedure

1. Translate the brief into a delivery promise: duration, aspect ratio, audience, platform, hook, visual mode, narration, music, captions, and source footage. Completion: the requested format and creative ingredients are explicit.
2. Select a pipeline from `pipeline_defs/`. Read its manifest and the relevant stage-director skill before executing that stage. Completion: required tools, fallbacks, and approval gates are known.
3. Run preflight with `provider_menu_summary()` and present capabilities grouped by video, image, TTS, music, and composition. Completion: the user sees what is available now and what optional keys/installations unlock.
4. For consequential generation, announce exact tool, provider, model/variant, reason, and whether it is a sample or batch. Completion: the choice is communicated before spend or generation.
5. At proposal, present Remotion and HyperFrames separately whenever both are available, plus FFmpeg where applicable. Explain the best fit and tradeoff, recommend one, and wait for approval. Also present templated versus atelier authoring mode for meaningful work.
6. Initialize `projects/<project-id>/` and open Backlot when possible. Keep every artifact and asset under that workspace. Completion: `project.json`, checkpoints, and canonical artifact paths exist.
7. Execute stages one at a time. Read each director skill and any referenced provider skill before tool use. Pause at human approval gates; never mark a gated stage complete without approval.
8. Produce captions from the actual transcript/timestamps, clean and mix audio, and render with the approved runtime. Completion: the final render exists at `projects/<project-id>/renders/final.mp4`.
9. Run the built-in post-render review: ffprobe, sampled frames, audio levels, delivery-promise validation, and subtitle checks. Completion: review passes or the blocker is reported with options; never present an unverified render.
10. Generate title, caption, thumbnail-text, and scheduling metadata only after the video passes QA. Keep these as project artifacts and distinguish drafts from approved publishing assets.

## Recommended Brief Templates

Screen demo:

```text
Make a <duration> <platform/aspect> screen-demo about <topic>.
Structure: 0-5s face/hook; <range> screen recording + voiceover;
final <range> face/conclusion. Add word-level captions, clean audio,
and a concise title/thumbnail text. Use real app capture only when needed;
use a synthetic terminal scene for CLI/install demonstrations.
```

Explainer:

```text
Make a <duration> <platform/aspect> animated explainer about <topic>
for <audience>. Hook: <hook>. Use <voice/music> and burned-in captions.
Prefer motion-led visuals, explain <key points>, and show the cost before
paid generation. Stop for script, scene-plan, asset, and publish approvals.
```

Documentary/B-roll:

```text
Make a <duration> real-footage documentary montage about <topic>.
Use real footage only from open/archive/stock sources, with <narration/music>
and captions <yes/no>. Do not substitute still-image animation for a
motion-led promise without asking.
```

## Pitfalls

- Never skip pipeline selection, preflight, stage skills, checkpoints, or QA.
- Never silently switch provider, model, runtime, motion-led treatment, narration, music, or batch/sample mode.
- Never place generated output in the repository root or temp directory.
- Never expose or commit `.env` secrets.
- If the approved runtime or provider is unavailable, stop and explain what failed, why, and the approved alternatives.
- OpenMontage is AGPL-3.0; review licensing before redistributing a modified system or generated asset whose source has separate terms.

## Verification

- `make preflight` returns the live capability menu.
- The selected pipeline manifest and director skills were read.
- Project checkpoints show approvals for gated stages.
- `projects/<project-id>/renders/final.mp4` exists.
- Post-render review passes ffprobe, frame, audio, delivery, and subtitle checks.
- Final response includes the exact output path and any provider/cost limitations.
