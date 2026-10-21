# Studio artifact boundary

Each revision is an OpenMontage project directory. The runner supplies its absolute path and sets `OPENMONTAGE_PROJECTS_DIR` to the revision's parent. Use `r001`, `r002`, etc. as the checkpoint project ID, so files stay in the active revision. Use `brief.json.pipeline_type` (an absolute manifest stem) with the OpenMontage loader/checkpoints. Load script and scene schemas directly from OpenMontage rather than maintaining copies here. Source review in `artifacts/research_brief.json` is a concise Studio source record; the upstream five-source long-form research schema does not apply to this short workflow. Never invent additional sources.

Required outputs:

| Phase | Files | Boundary |
|---|---|---|
| script | `artifacts/research_brief.json`, `artifacts/script.json`, `artifacts/scene_plan.json`, `SCRIPT.md`, `PHONETICS.md` | No asset generation before user approval |
| preview | `artifacts/voice_check.json`, `artifacts/asset_manifest.json`, edit decisions, composition, playable preview MP4, `POST_METADATA.md`, `artifacts/post_metadata.json`, `audio_meta.json` | Stop for preview review |
| final | Final H.264/AAC MP4, `artifacts/final_review.json`, existing preview | No publication or cleanup |

`script.json` and `scene_plan.json` must validate against `OpenMontage/schemas/artifacts/`. Scene IDs are unique and stable. Scene timing starts at zero, covers the full duration without gaps/overlaps, and references valid script section IDs. Retain evidence URLs per factual section.

Write `studio_result.json` only after a phase is complete:

```json
{"phase":"preview","preview":"renders/preview.mp4","summary":"Preview đã sẵn sàng để duyệt."}
```

Final phase preserves the `preview` path and adds `final`. Paths are relative to this revision and must resolve to real files inside it. A blocker instead uses `{"phase":"preview","blocked":true,"blocker":"Specific missing input or failed capability"}`. Completion is verified independently; do not invent success artifacts.

`qa_report.json` is owned by the backend, not the agent. Approval records and schedules live in SQLite and refer to the revision fingerprint; production code must not edit them.
