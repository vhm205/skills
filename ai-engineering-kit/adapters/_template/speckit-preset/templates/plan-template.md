## Project Verification Matrix *(CHANGE-ME project)*

<!-- Example section appended to every plan. Replace or delete. -->

| Gate | Command | When |
|---|---|---|
| Fast loop | `<verify.test_fast>` | after each task |
| Final gate | `<verify.test_full>` | before DONE / PR |
| Frontend | `<verify.fe_test>` | when the UI changed |
| Acceptance | `<verify.uat>` | before release |

- **Baseline:** `<baselines or "none">`; green means no failures beyond it.
- **Risk areas touched:** `<paths>` — if behavior changes here, the lane is LARGE.
- **Rollback:** `<how to revert safely>`; state whether data needs repair.

## Documentation Authority *(CHANGE-ME project)*

- This plan owns behavior/design for one slice; product intent stays in `<product docs>`,
  architecture in `<architecture docs>`, status in `<tracker>`, evidence in `<QA/evidence>`.
- Link, never copy. If a fact changes, edit its owner and amend this plan's delta.
