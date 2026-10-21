# Shared Vietnamese production contract

Workspace `AGENTS.md` owns detailed voice and audio constraints. This reference keeps only cross-workflow invariants.

- Narration: natural Vietnamese with concrete details, varied sentence lengths and no AI hype, fake personal experience, empty rhetorical contrast or stock closers. Apply Humanizer principles; load an installed `humanizer` skill when available. Separate researched fact from opinion.
- Default visuals: real source screenshots/recordings first, minimal overlays and purposeful motion. Caption language is independently configurable; preserve the brief.
- Keep `script.json` clean. Put engine-ready text in section `delivery_cues.provider_text`; keep display/caption terms correctly spelled. Write `PHONETICS.md` with original term, engine and chosen pronunciation.
- OmniVoice reference file is workspace `ref_voice.wav`, with exact `ref_text="Hôm nay, thời tiết rất đẹp, chúc các bạn có một ngày làm việc hiệu quả."`. Never invent the reference transcript. Do not pair a different reference recording with this transcript.
- No target duration passed to OmniVoice. Synthesis speed 1.08–1.12; FFmpeg `atempo` 1.10–1.14 afterward. Never raw diffusion speed above 1.20. Preserve Vietnamese tones and avoid sluggish or rushed narration.
- OmniVoice: CPU→`si pi u`, vCPU→`vi si pi u`, API→`A-P-I`/`ây pi ai`, AI→`A-I`/`ây ai`, Agent→`ây dần`, C#→`C Sharp`. Keep `framework...` rather than crude phonetic spelling. VieNeu keeps standard English terms for bilingual G2P.
- Expand numbers/symbols into spoken Vietnamese; add natural clause pauses. Do not leave long clauses without breath points. Check spelling before synthesis.
- Sample gate: generate a technical-term sample, listen or verify with available speech recognition, fix pronunciation errors, then create batch audio. Save `artifacts/voice_check.json` with `passed`, `method`, `terms_checked`, `evidence` (relative files). If no reliable check is available, stop for human listening; do not mark it passed.
- Voice foreground 1.0, normalize to -14 LUFS / -1.5 dBTP; BGM under speech default 0.04, never above 0.06. Review combined output on the actual mix.
- Translate English captions from the final Vietnamese clean narration and align by phrase boundaries. Never force Vietnamese delivery to follow English caption text.
- Use the approved runtime; read its installed HyperFrames/Remotion skills at the active stage. Validate, preview and inspect actual rendered frames before release.
- Paid services require a separate named provider/model/cost approval. Default to local tools and existing assets. A blocked choice must be surfaced, not silently replaced.
