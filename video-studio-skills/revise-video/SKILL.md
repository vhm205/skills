---
name: revise-video
description: Apply scoped follow-up changes to a Studio video scene, narration, caption or mix while preserving previous revisions and unaffected media.
---

# Revise video

Identify the project, current revision and requested scene IDs or timestamp first. Read the current script, scene plan and previous output before editing.

In chat use `studio/.venv/bin/python studio/cli.py show <id>` then `revise <id> --prompt '...' --scope visual|narration|caption|audio|script|all [--scene <id>] [--timestamp <seconds>]`. The command creates a revision and returns its impact; it never approves or runs it automatically. Let the user review the new revision in Studio. Do not mutate the old revision directly.

In managed mode, read `revision_request.json`. Write only inside the new revision. Existing media are independent copies and may be reused unchanged; the parent revision is immutable.

| Request | Change | Preserve |
|---|---|---|
| Visual | Selected imagery, framing, overlays, composition | Script, narration, audio timing |
| Narration | Selected provider text/audio, phrase caption alignment, subsequent timeline offsets | Unchanged scene IDs and unrelated assets |
| Caption | Selected caption text/style/layout | Narration and source visuals |
| Audio | BGM/SFX and final mix | Narration files, script and imagery |
| Script/all | Requested script and its dependent assets | Everything outside the explicit request |

Write a concise change summary and dependency impact. Never rewrite unaffected narration to “improve consistency”. After narration duration changes, use measured audio lengths to recalculate caption/scene timing. For visual-only changes, verify unchanged audio files by hashes before completing. Render a new preview and stop for approval.

A restoration creates a new revision from a prior version; it does not overwrite history. Any future schedule affected by revisions must be reviewed in Studio. Remote uploads already underway must be reconciled before editing.
