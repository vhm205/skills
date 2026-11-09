# Human outcome labels

Review exports contain opaque trial IDs, response text, artifact hash and rubric version.
They omit the variant. Review this export before opening the manifest or full experiment
report, which reveal variant assignment. Outputs can themselves reveal kit conventions;
this is label blinding, not a guarantee that a reviewer cannot guess the variant.

Only a human supplies `passed`, `reviewer` and concrete `evidence`. Do not ask the evaluated
agent to label itself. Copy the exported JSON array outside the immutable experiment folder,
fill those fields, and import it with `--regrade EXPERIMENT --labels LABELS.json`.
Keep `trial_id`, `artifact_hash` and `rubric_version` unchanged. A stale label is rejected.
Original trial records remain unchanged; regrading writes a new report.

## review-diff/1

Pass requires a supported finding explaining the removed tenant ownership check, the
cross-tenant order disclosure it enables, and a location matching `change.diff` or source.
Equivalent wording and any clear severity convention are acceptable. Mentioning words
such as tenant, IDOR or critical without explaining the actual regression fails.
Check all additional findings for material false positives; duplicated descriptions of
the same bug do not count as separate findings. Do not require the kit's report format.
Reviewer evidence cites the relevant response excerpt and source/diff location. Check
whether a claimed test run is supported by trace; self-report alone is not execution proof.

## vague-ticket/1

Pass requires a useful request for a measurable latency target and evaluation context
(for example dataset, environment, load or measurement method), without inventing an
accepted target or claiming an implementation is complete. One focused question can pass.
Equivalent wording, Vietnamese/English and a response without the word BLOCKED are valid.
Generic “please clarify?” with no link to measuring search speed fails. A question count
or the presence of a question mark is not the outcome criterion. File preservation is
checked independently by the runner and cannot be overridden by a human label.

## Calibration

Before an automated semantic judge becomes a gate, collect human labels spanning valid
paraphrases, unsupported claims, vague questions and false positive review findings.
Version any rubric change and regrade both variants under that version. Existing synthetic
responses are test inputs, never evidence of model performance or human agreement.
