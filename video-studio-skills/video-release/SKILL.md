---
name: video-release
description: Verify a Studio video release, prepare clean platform metadata and export bundles, and track explicit publication approval without claiming unverified uploads.
---

# Video release

Read [production](../references/production.md) and [artifact contract](../references/artifacts.md). Final output requires a real MP4, technical QA and visual/caption review; a successful render command alone is insufficient.

Inspect frame samples around transitions and captions. Check source truth, spelling, narration pronunciation, safe framing and readability. Check actual encoding, portrait dimensions, duration, decode errors, black gaps and loudness. Backend independently creates `qa_report.json`; do not forge or edit that report.

Write `artifacts/post_metadata.json` keyed by `youtube`, `facebook`, `tiktok`, each with `title`, `description`, `hashtags` (maximum five). Write `POST_METADATA.md` with clean code blocks containing only the copyable values. No `>` blockquotes, `<`/`>` characters, vertical bars or embedded “Title:”/“Hashtags:” labels in values.

The user approves the exact final revision and confirms each platform/account/schedule in Studio. Do not call social publishing tools from a production agent. A scheduled item, returned upload ID or processing status is not proof of publication.

Record manual receipts as user-confirmed, API receipts as platform-verified. Preserve media while any selected destination remains pending or failed. Only Studio's explicit archive action may invoke `scripts/post_publish.py` after all destinations are published or explicitly skipped; retain lightweight receipts and remove heavy revision/export media.
