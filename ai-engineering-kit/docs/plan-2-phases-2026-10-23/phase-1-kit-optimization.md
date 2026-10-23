# Phase 1 — Tối ưu bộ skills AI Engineering Kit

**Trạng thái:** Đã triển khai (Phase 1) trên nhánh `feat/phase-1-kit-optimization`; trigger gate PASS (`dsh` 92,0%), behaviour gate PASS trên evidence per-scenario cuối cùng (real `dsh` 7/7, 0 critical; raw one-pass 3/7 preserved; mock 7/7 synthetic) — xem [handover](../phase-1-handover.md).
**Phạm vi:** chỉ `ai-engineering-kit/`. Không thay đổi Orchexa, không cài Spec Kit vào Orchexa.
**Nguồn:** [Đánh giá & đề xuất 2026-10-23](../skills-audit-and-plan-2026-10-23.md).
**Thời lượng dự kiến:** 3–4 tuần (1 kỹ sư + agent review).
**Đầu ra cuối Phase 1:** kit đạt best practice Agent Skills, có eval/script/profile, sẵn sàng cho [Phase 2](phase-2-orchexa-spec-kit-integration.md).

---

## 0. Mục tiêu & kết quả mong đợi

| # | Kết quả | Tiêu chí đo | Bằng chứng |
|---|---|---|---|
| 1 | Triggering đúng | 15/15 description theo mẫu "Use when… + triggers + not for…"; trigger eval ≥ 90% | `evals/trigger.json`, báo cáo eval |
| 2 | Format & progressive disclosure | 15/15 `SKILL.md` ≤ 120 dòng; references hợp lệ; không field lạ (trừ allowlist) | `scripts/check.sh` PASS |
| 3 | Scripts cho việc lặp | 4 script chạy được: resolve adapter, verify evidence, worktree, traceability | test script + demo output |
| 4 | Evals hành vi | 7 scenario; with/without; ≥ 80% pass; 0 critical safety failure | `evals/` + benchmark |
| 5 | Install profile | `--profile core\|discovery\|full`; `core` cài đúng 11 skill | `install.sh` test + dry-run |
| 6 | Adapter contract v2 | `planning`, `repos`, `test_fast/full`, `baselines`, `worktree_name_pattern`, `{ticket}`, adapter refs/scripts | `core/adapter-contract.md` + checker |
| 7 | Workflow nhất quán | PR ownership rõ; risk-area semantics rõ; TDD title đúng | review + `check.sh` |
| 8 | Tài liệu & release | README tách; guide cập nhật; version/changelog | `README.md`, `docs/`, release note |
| 9 | Không phá vỡ | `check.sh`, `test.py`, `test-speckit.py`, install dry-run PASS | CI/local log |
| 10 | Không chạm Orchexa | 0 file Orchexa thay đổi | `git status` ngoài kit |

**Không làm trong Phase 1:** không sửa adapter/skills Orchexa; không cài Spec Kit vào Orchexa;
không gộp 23 skill Orchexa; không trim `AGENTS.md`/`CLAUDE.md` của Orchexa; không migrate docs Orchexa.
Những việc đó thuộc Phase 2.

---

## 1. Nguyên tắc thực hiện

1. **Không tạo general skill mới.** Chỉ cải thiện 15 skill hiện có; nếu phát sinh nhu cầu mới,
   phải đủ 5 tiêu chí ở [audit §5.5](../skills-audit-and-plan-2026-10-23.md).
2. **Không đổi workflow.** Một planner (Spec Kit hoặc external qua `planning`), một nguồn sự thật
   cho mỗi loại artifact, ba handoff BLOCKED/NEEDS DECISION/DONE.
3. **Thay đổi description phải có eval.** Không merge description mới nếu trigger eval giảm.
4. **Scripts là optional, an toàn.** Non-interactive, có `--help`, in command trước khi chạy,
   không chạy deploy/merge, không đọc secret.
5. **Backward compatible.** Adapter cũ vẫn chạy; profile mặc định giữ nguyên `full`; script mới
   không bắt buộc.
6. **Đo trước, sửa sau.** P1.0 chụp baseline trước khi đổi description/format.

---

## 2. Workstreams & tasks

### P1.0 — Baseline & guardrails (2–3 ngày)

**Mục tiêu:** có thước đo và checker trước khi sửa.

| ID | Task | File / artifact | Acceptance |
|---|---|---|---|
| T01 | Viết `scripts/check_skills.py` dùng chung kit/project | `scripts/check_skills.py` | Kiểm tra `SKILL.md` đúng case, frontmatter, `name` = thư mục, description ≤ 1.024, body ≤ 250, link refs, parity `.claude`/`.agents` (nếu có); exit code rõ |
| T02 | Tạo bộ trigger eval | `evals/trigger.json`, `scripts/eval_trigger.py` | 25 query (15 should, 10 near-miss); chạy được 1 harness; ghi `SKILL_USED`/log |
| T03 | Tạo fixture + skeleton behavior eval | `evals/tasks/`, `scripts/eval_tasks.py` | 7 scenario fixture; chạy được 1 scenario end-to-end |
| T04 | Chụp baseline | `docs/skills-baseline-2026-10-23.md` | Trigger accuracy hiện tại, số skill gọi sai, token/thời gian 5 task mẫu |

**Acceptance P1.0:** checker chạy trên kit; baseline có số; chưa sửa skill nào.

### P1.1 — Triggering & format (4–6 ngày)

**Mục tiêu:** description nói đúng "khi nào gọi", format đồng nhất.

| ID | Task | File / artifact | Acceptance |
|---|---|---|---|
| T05 | Viết lại 15 description theo mẫu `Use when…` + trigger + `Not for` | `skills/*/SKILL.md` | 15/15 có trigger phrase; 0 description bắt đầu bằng "Applies/Checks/Reviews/Shapes" đơn thuần; ≤ 1.024 ký tự |
| T06 | Thêm negative trigger + "Gotchas" ngắn | 5 skill hay nhầm: `verifying-change`, `reviewing-change`, `executing-task`, `systematic-debugging`, `using-worktrees` | Mỗi skill có 1 mục "Gotchas" 3–6 dòng; negative trigger rõ |
| T07 | Xử lý root `SKILL.md` | root `SKILL.md` hoặc `KIT.md` | Chọn một: meta-skill được cài, hoặc `KIT.md` + bỏ khỏi `package.json.files`; ghi lý do trong README |
| T08 | Chính sách `compatibility`/`metadata` | `scripts/check.py`, `AGENTS.md` | Cho phép `compatibility` (nếu chọn) hoặc ghi dependency `.aiek/` trong README; checker cập nhật |
| T09 | Sửa tiêu đề TDD | `skills/test-driven-development/SKILL.md` | Bỏ "(optional)" → "(adapter-controlled)"; nội dung nói rõ adapter quyết định |
| T10 | Tách README | `README.md`, `docs/local-review-ui.md` | README còn workflow/skills; UI/Copilot sang docs riêng; link chéo |
| T11 | Cập nhật guide | `docs/huong-dan-workflow.md` | 15 skill, profile, eval mới; không còn câu "chưa có eval" |

**Acceptance P1.1:** trigger eval không giảm; `check.sh` PASS; 15/15 description đúng mẫu; 0 mâu thuẫn TDD/root SKILL.

### P1.2 — Workflow correctness (2–3 ngày)

**Mục tiêu:** hết mâu thuẫn giữa skill/core.

| ID | Task | File / artifact | Acceptance |
|---|---|---|---|
| T12 | Chốt PR ownership | `core/WORKFLOW.md`, `skills/authoring-pr/SKILL.md`, `skills/finishing-branch/SKILL.md` | `authoring-pr` viết body; `finishing-branch` chọn merge/PR/keep và dùng body; không skill nào tự merge/push nếu chưa được yêu cầu |
| T13 | Làm rõ risk-area semantics | `core/classification.md`, `core/adapter-contract.md` | Behavior-neutral edit trong risk path không tự động LARGE; vẫn cần human review nếu adapter yêu cầu; behavior change vẫn LARGE |
| T14 | Ghi `planning` mode vào router/contract | `core/router.md`, `core/adapter-contract.md` | Có `speckit \| external \| none`; skill đọc artifact theo mode; không tạo plan thứ hai |
| T15 | Handoff/report language | `core/handoffs.md`, `adapters/_template` | Nói rõ `output_language` áp cho PR/report; DONE có thể ngắn cho Small |
| T16 | Cập nhật install docs | `docs/adding-an-adapter.md`, `README.md` | Hướng dẫn adapter v2 + profile + script + docs authority |

**Acceptance P1.2:** không còn mâu thuẫn PR ownership; 0 mâu thuẫn planner; `check.sh` PASS.

### P1.3 — Capabilities cho Phase 2 (6–8 ngày)

**Mục tiêu:** kit có sẵn cơ chế để Phase 2 cấu hình Orchexa mà không sửa core.

| ID | Task | File / artifact | Acceptance |
|---|---|---|---|
| T17 | Adapter contract v2 | `core/adapter-contract.md` | Thêm `planning`, `repos`, `verify.test_fast/test_full`, `baselines`, `worktree_name_pattern`, `{ticket}`, `adapter.references/scripts`; backward compatible |
| T18 | Install profiles | `scripts/install.sh`, `manifest.json` | `--profile core\|discovery\|full`, `--only`, `--skip`; `core` = 11 skill; test inventory |
| T19 | Resolve adapter script | `scripts/resolve_adapter.py` (hoặc `.aiek/scripts/`) | Parse YAML + auto-discovery; output JSON; không chạy command |
| T20 | Verify script | `scripts/verify.py` | Chạy `verify.*`, lưu `evidence.md`/`evidence.json`, so baseline; `--scope`, `--only`, `--json`, `--dry-run`; in command trước khi chạy |
| T20b | Cập nhật skill dùng script + fast/full | `skills/verifying-change`, `skills/executing-task`, `skills/using-worktrees` | `verifying-change` dùng `verify.py`/`test_fast`/`test_full`; `using-worktrees` dùng `worktree.py`; mô tả rõ `test` vs `test_fast` |
| T21 | Worktree script | `scripts/worktree.py` | Chọn dir/name pattern/branch, ignore, copy artifact, setup/baseline; không `--force`, không xoá worktree khác |
| T22 | Traceability script | `scripts/traceability.py` | Mỗi AC có row/bucket/proof; output lỗi rõ |
| T22b | Cập nhật `intaking-ticket` dùng script | `skills/intaking-ticket/SKILL.md` | Gọi `traceability.py` sau khi lập bảng; lỗi rõ nếu thiếu row |
| T23 | Hỗ trợ `speckit-preset` + docs authority | `core/adapter-contract.md`, `docs/adding-an-adapter.md`, `adapters/_template/speckit-preset/` | Preset append/wrap; mẫu constitution/spec/plan/tasks; quy định docs nào sở hữu fact nào |
| T24 | Test script/installer | `tests/`, `scripts/test.py`, `scripts/test-speckit.py` | Test 4 script; test 3 profile; test preset composition; CI |

**Acceptance P1.3:** cài `--profile core` vào fixture; 4 script chạy được; adapter v2 checker PASS; test-speckit PASS; 5 skill liên quan đã cập nhật để dùng script.

### P1.4 — Evals (4–5 ngày)

**Mục tiêu:** có bằng chứng định lượng, không chỉ review tĩnh.

| ID | Task | File / artifact | Acceptance |
|---|---|---|---|
| T25 | Trigger eval 25 query | `evals/trigger.json`, `scripts/eval_trigger.py` | Chạy 3 lần/query; precision/recall; near-miss pass nếu không gọi skill |
| T26 | Behavior eval 7 scenario | `evals/tasks/`, `scripts/eval_tasks.py` | Small, Normal, bug, ticket mơ hồ, review diff, infra, parallel; assertions cụ thể |
| T27 | With/without + benchmark | `evals/results/`, `benchmark.json` | So pass rate, token, thời gian; human review 10 mẫu |
| T28 | CI eval | `.github/workflows/` hoặc `scripts/check.sh` | PR: 10 trigger + 2 behavior; nightly full |
| T29 | Báo cáo kết quả | `docs/eval-2026-10-23.md` | Trigger ≥ 90%; behavior ≥ 80%; 0 critical; ghi rõ giới hạn |

**Acceptance P1.4:** trigger ≥ 90%; behavior ≥ 80%; 0 critical; CI chạy.

### P1.5 — Docs & release (2–3 ngày)

| ID | Task | File / artifact | Acceptance |
|---|---|---|---|
| T30 | README/guide/examples | `README.md`, `docs/huong-dan-workflow.md`, `docs/adding-an-adapter.md` | Phản ánh 15 skill, profile, scripts, evals |
| T31 | Version/manifest/changelog | `manifest.json`, `package.json`, `CHANGELOG` (nếu có) | Version khớp; checker PASS |
| T32 | Chạy toàn bộ kiểm tra | `scripts/check.sh`, `scripts/test.py`, `scripts/test-speckit.py`, install dry-run | Tất cả PASS; log lưu |
| T33 | Release note + handover | `docs/phase-1-handover.md` | Tóm tắt thay đổi, metric, việc còn lại cho Phase 2 |

**Acceptance P1.5:** release sẵn sàng; handover có checklist.

---

## 3. Danh sách thay đổi file-level

| Ưu tiên | File | Thay đổi | Liên quan |
|---|---|---|---|
| P0 | `scripts/check_skills.py` | Mới: checker metadata/body/parity | T01 |
| P0 | `evals/trigger.json`, `scripts/eval_trigger.py` | Mới: trigger eval | T02, T25 |
| P0 | `evals/tasks/`, `scripts/eval_tasks.py` | Mới: behavior eval | T03, T26 |
| P1 | `skills/*/SKILL.md` (15) | Description + gotchas + negative trigger | T05, T06 |
| P1 | root `SKILL.md` / `KIT.md` | Xử lý entry không được cài | T07 |
| P1 | `scripts/check.py` | Allowlist field; check body/desc | T08 |
| P1 | `core/WORKFLOW.md` | PR ownership, planning mode | T12, T14 |
| P1 | `core/classification.md` | Risk semantics | T13 |
| P1 | `core/router.md` | Planning/profile note | T14 |
| P1 | `core/handoffs.md` | Report language | T15 |
| P1 | `core/adapter-contract.md` | v2 keys + docs authority | T17, T23 |
| P1 | `scripts/install.sh` | Profiles, adapter refs/scripts | T18 |
| P1 | `scripts/resolve_adapter.py` | Mới | T19 |
| P1 | `scripts/verify.py` | Mới | T20 |
| P1 | `skills/verifying-change`, `skills/executing-task`, `skills/using-worktrees` | Dùng script + `test_fast`/`test_full` | T20b |
| P1 | `scripts/worktree.py` | Mới | T21 |
| P1 | `scripts/traceability.py` | Mới | T22 |
| P1 | `skills/intaking-ticket/SKILL.md` | Dùng `traceability.py` | T22b |
| P1 | `adapters/_template/speckit-preset/` | Mẫu constitution/spec/plan/tasks | T23 |
| P1 | `docs/adding-an-adapter.md` | v2 + preset + docs authority | T16, T23 |
| P1 | `README.md`, `docs/local-review-ui.md` | Tách README | T10 |
| P1 | `docs/huong-dan-workflow.md` | 15 skill/profile/eval | T11, T30 |
| P2 | `manifest.json`, `package.json` | Version | T31 |
| P2 | `docs/skills-baseline-2026-10-23.md`, `docs/eval-2026-10-23.md`, `docs/phase-1-handover.md` | Mới | T04, T29, T33 |

Không đổi: `speckit/` command logic, workflow stages, handoff format, 15 skill ownership.

---

## 4. Eval plan (chi tiết)

### 4.1. Trigger eval

Dùng bộ 25 query ở [audit §8.1](../skills-audit-and-plan-2026-10-23.md), tối thiểu gồm:

- 15 should-trigger: Small fix, implement task, bug unknown cause, flaky test, review diff, PR description, release readiness, idea, feature shaping, ticket AC, worktree, parallel, deploy, TDD, merge.
- 10 near-miss negative: explain function, SQL query, review essay, run tests, update README, open PR, AC "fast", new project BRD, migrate DB, "should we…".

Quy tắc:
- 3 lần/query; majority.
- Acceptable set cho query mơ hồ (`open the PR` → `finishing-branch` hoặc `authoring-pr`).
- Negative pass nếu **không** gọi skill.
- Ghi cả "wrong skill" để phân tích nhầm lẫn.

### 4.2. Behavior eval

7 scenario: Small fix, Normal feature, bug, ticket mơ hồ, review diff, infra, parallel.

Assertions tối thiểu:
- Lane statement đúng; artifacts đúng (không spec cho Small; spec/plan/tasks cho Normal).
- DONE có bảng evidence (command/exit code); không claim DONE trước check.
- Ticket mơ hồ → BLOCKED + câu hỏi; không code.
- Review diff → finding `file:line` + severity.
- Infra → decision/rollback rehearsal/evidence.
- Parallel → quyết định + worker brief + combined verification.

### 4.3. With/without & metric

- Mỗi scenario chạy 2 lần: có skill / không skill.
- Ghi pass rate, token, thời gian, số lần can thiệp.
- Human review 10 output mẫu, chấm theo rubric.
- Ngưỡng: trigger ≥ 90%; behavior ≥ 80%; 0 critical.
- CI: PR 10 trigger + 2 behavior; nightly full; lưu `benchmark.json`.

---

## 5. Scripts plan

| Script | Interface | Output | Safety |
|---|---|---|---|
| `resolve_adapter.py` | `--adapter PATH --repo PATH --json` | JSON command đã resolve | Chỉ đọc; không chạy |
| `verify.py` | `--adapter PATH --scope changed --only test,lint --json --dry-run` | `evidence.md`, `evidence.json` | In lệnh; timeout; không chạy deploy/merge; không đọc secret |
| `worktree.py` | `--adapter PATH --slug x --ticket OSA-123 --setup --baseline` | worktree + baseline | Không `--force`; kiểm tra path; không xoá worktree khác |
| `traceability.py` | `--file spec.md --json` | lỗi/thiếu row | Chỉ đọc |

Quy ước:
- Python 3 (kit đã yêu cầu cho installer); không Bash-only.
- `--help`, exit code 0/1/2; lỗi nêu cách sửa.
- Mọi command in ra trước khi chạy; mặc định `--dry-run` cho lệnh nguy hiểm.
- Script đặt ở `scripts/` của kit và được cài vào `.aiek/scripts/` để skill gọi ổn định.

---

## 6. Adapter contract v2 — Phase 2 enabler

Thêm các key sau (backward compatible):

| Key | Ý nghĩa | Dùng bởi |
|---|---|---|
| `planning.mode` | `speckit \| external \| none` | `executing-task`, router |
| `planning.plan_path` / `task_source` | Artifact nguồn khi external | `executing-task` |
| `repos` | Map repo (BE/FE) | `verifying-change`, `using-worktrees` |
| `verify.test_fast` / `test_full` | Fast lane vs final gate | `executing-task`, `verifying-change` |
| `verify.fe_*` | Lệnh FE tường minh | Task loop |
| `verify.ui` / `run_fe` | Quan sát UI | `verifying-change` |
| `baselines` | Nhiều baseline (prose/file/command) | `verifying-change`, TDD |
| `worktree_name_pattern` | `{repo}-wt-{slug}` | `using-worktrees` |
| `branch_pattern` tokens | `{feature}`, `{slug}`, `{type}`, `{ticket}` | `using-worktrees` |
| `adapter.references` / `scripts` | Tài liệu/script project-specific | Installer |

Thêm `core/documentation.md` (hoặc mục trong `adapter-contract.md`) quy định:
- Fact nào thuộc `docs/`, fact nào thuộc `specs/`, fact nào thuộc `AGENTS.md`/`.aiek`/`.specify`.
- Không tạo plan thứ hai; link thay vì copy.
- `specs/` là feature execution layer; docs là durable knowledge.
Đây là cơ sở để Phase 2 áp dụng cho Orchexa mà không cần sửa core.

---

## 7. Definition of Done (Phase 1)

Chạy:

```bash
cd ai-engineering-kit
UV_CACHE_DIR=/tmp/aiek-uv-cache bash scripts/check.sh
mkdir -p /tmp/aiek-fixture
bash scripts/install.sh /tmp/aiek-fixture --harness codex --dry-run
bash scripts/install.sh /tmp/aiek-fixture --harness codex --profile core --dry-run
python scripts/test.py          # cần PyYAML
python scripts/test-speckit.py  # cần specify trên PATH
```

Kỳ vọng:
- `check.sh`: PASS 15 skills + inventories.
- `install.sh --dry-run`: PASS; `--profile core` đúng 11 skill.
- `test.py`: PASS; `test-speckit.py`: PASS 3 integration.
- Trigger eval ≥ 90%; behavior ≥ 80%; 0 critical.
- 0 file Orchexa thay đổi.
- Handover `docs/phase-1-handover.md` có danh sách capability cho Phase 2.

Review checklist:
- [ ] 15/15 description có trigger + negative.
- [ ] Không còn mâu thuẫn PR ownership/planner.
- [ ] 4 script có test + `--help`.
- [ ] Profile core/discovery/full đúng.
- [ ] Adapter v2 không phá adapter cũ.
- [ ] Docs authority được mô tả.
- [ ] README/guide cập nhật.
- [ ] Eval có số, không chỉ "cảm giác".

---

## 8. Timeline & owners

| Tuần | Việc | Owner | Dependency |
|---|---|---|---|
| 1 | P1.0 baseline; bắt đầu T01–T04 | Kit maintainer | — |
| 2 | P1.1 descriptions/format; P1.2 workflow | Kit maintainer + reviewer | P1.0 |
| 3 | P1.3 capabilities/scripts; P1.4 eval | Kit maintainer | P1.1, P1.2 |
| 4 | Hoàn thiện eval, P1.5 docs/release, review | Kit maintainer + reviewer | P1.3 |
| Sau Phase 1 | Gate review → Phase 2 | Tech lead | Phase 1 DoD |

Ước lượng: 15–20 ngày làm việc; có thể rút còn 3 tuần nếu P1.1/P1.2 chạy song song.

---

## 9. Rủi ro & giảm thiểu

| Rủi ro | Mức | Giảm thiểu |
|---|---|---|
| Description mới làm trigger regress | Cao | Eval trước/sau; chỉ merge khi ≥ baseline; acceptable alternatives |
| Profile/installer phá install cũ | Cao | Dry-run; test 3 profile; giữ `full` mặc định |
| Script chạy lệnh nguy hiểm | Cao | Read-only mặc định; in command; `--dry-run`; không deploy/merge; test |
| Adapter v2 phá adapter cũ | Trung bình | Key optional; checker; test với default/orchexa template |
| Eval tốn thời gian | Trung bình | PR quick 10 query; nightly full; cache |
| Scope creep sang Orchexa | Cao | Gate: Phase 1 chỉ `ai-engineering-kit/`; mọi việc Orchexa → Phase 2 |
| Root SKILL thay đổi gây nhầm | Thấp | Ghi rõ trong README/checker; bỏ khỏi package nếu chọn KIT.md |

---

## 10. Bàn giao sang Phase 2

Phase 1 phải bàn giao:
- `planning` mode + docs authority trong adapter contract.
- `speckit-preset` mẫu (constitution/spec/plan/tasks) + docs.
- `--profile core` + `--only/--skip`.
- `resolve_adapter.py`, `verify.py`, `worktree.py`, `traceability.py`.
- Trigger/behavior eval + CI.
- Adapter v2 + test.
- Báo cáo metric baseline/sau.

Phase 2 sẽ dùng các năng lực này để cấu hình Orchexa mà không sửa core. Xem
[Phase 2](phase-2-orchexa-spec-kit-integration.md).
