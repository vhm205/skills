# Human review — DSH API pilot 2026-11-09

Status: 12 outcomes pending. No human or automated semantic labels have been applied.
Variant labels are omitted here. Responses may still reveal kit conventions; blinding is imperfect.
Review this file before opening the aggregate report/manifest.

Rubrics: [review-diff/1 and vague-ticket/1](../labels/README.md).
Fill `passed` (true/false), `reviewer` and concrete excerpt/source `evidence` in
[the editable labels copy](pilot-dsh-api-2026-11-09-human-labels.json).
Preserve trial IDs, artifact hashes and rubric versions. Do not use mock labels.

Then import without another model call:

```bash
python3 scripts/eval_tasks.py --regrade evals/results/local/pilot-dsh-api-fixed-2026-11-09 \
  --labels evals/results/pilot-dsh-api-2026-11-09-human-labels.json \
  --out evals/results/pilot-dsh-api-2026-11-09-graded.json
```


Read the 12 unmodified responses in [the plain-text packet](pilot-dsh-api-2026-11-09-human-responses.txt).

Transcript links are preserved as literal text; they refer to the evaluated workspace, not this report directory.
