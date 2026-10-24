# Đánh giá & kế hoạch cải thiện bộ skills — AI Engineering Kit + Orchexa

**Ngày:** 2026-10-23 · **Phạm vi:** `ai-engineering-kit/` (15 skills, core, Spec Kit, adapter) và
`orchexa-be` / `orchexa-fe` (23 + 1 skills, adapter Orchexa)
**Trạng thái:** đề xuất — tài liệu này không thay đổi code hay skill nào.
**Kế hoạch triển khai 2 phase:** [tổng quan](plan-2-phases-2026-10-23/README.md) ·
[Phase 1 — tối ưu kit](plan-2-phases-2026-10-23/phase-1-kit-optimization.md) ·
[Phase 2 — Orchexa + Spec Kit](plan-2-phases-2026-10-23/phase-2-orchexa-spec-kit-integration.md)
**Tài liệu tham chiếu:** [Quickstart](https://agentskills.io/skill-creation/quickstart) ·
[Best practices](https://agentskills.io/skill-creation/best-practices) ·
[Optimizing descriptions](https://agentskills.io/skill-creation/optimizing-descriptions) ·
[Evaluating skills](https://agentskills.io/skill-creation/evaluating-skills) ·
[Using scripts](https://agentskills.io/skill-creation/using-scripts) ·
[Specification](https://agentskills.io/specification)

---

## 0. TL;DR

**Kết luận:** kiến trúc của kit là đúng hướng và nên giữ; nó chưa "tối ưu" theo Agent Skills ở
bốn điểm lớn — **triggering**, **scripts**, **evals**, và **khả năng tái sử dụng ngoài Spec Kit**.
Bộ Orchexa có tri thức chuyên môn rất tốt nhưng chất lượng đóng gói kém; không nên viết thêm
skill general mới, mà nên **cải thiện kit rồi tái sử dụng**, đồng thời **gộp 23 skill Orchexa
thành 6 hub** có references/scripts/evals.

| # | Phát hiện chính | Bằng chứng |
|---|---|---|
| 1 | Kit có 15 SKILL.md ngắn (32–106 dòng), frontmatter hợp lệ, references rõ; `scripts/check.sh` PASS 15 skills | 1.059 dòng body, 3.632 ký tự description, 13 reference files |
| 2 | Description của kit thiên về mô tả ("Applies/Checks/Reviews…"), không có "Use when…", thiếu trigger phrase cụ thể và negative trigger | 0/15 bắt đầu bằng "Use when"; 10/15 không có "not for/excludes" |
| 3 | Kit **không có script nào trong skills** và **không có eval nào**; audit trước tự nhận "consistency review, not empirical benchmark" | 0 `skills/*/scripts`, 0 `evals/`; [audit 2026-10-17](audit-2026-10-17.md) |
| 4 | Kit phụ thuộc Spec Kit; Orchexa **không có** `.specify/` hay `specs/`, nên lane NORMAL/LARGE không chạy được nguyên trạng | kiểm tra filesystem Orchexa; `executing-task` yêu cầu `tasks.md` |
| 5 | Orchexa có 23 skills, 8.340 dòng body, 12.253 ký tự description; 5 skill không frontmatter, 7 file `skill.md` chữ thường, 2 description > 1.024 ký tự, 1 skill 1.475 dòng | script kiểm tra metadata (xem Phụ lục) |
| 6 | `.claude/skills` và `.agents/skills` của Orchexa đã drift 7 file; bản `.agents` mới hơn (2026-10-22 vs 2026-10-14) | `diff -rq`; mtime |
| 7 | Adapter Orchexa dài 229 dòng (contract khuyên < 150), chứa số liệu dễ hỏng và **3 tham chiếu đã chết**: `CLAUDE-Edupia.md`, skill `orchexa-edupia-trace-root-cause-from-profile`, `scripts/tom_tat.py` | commit `e703d52`, `ca5fab8`; `find` không thấy file |
| 8 | `AGENTS.md` và `CLAUDE.md` của Orchexa mỗi file 999 dòng / 50.458 byte, chỉ khác H1 → 50 KB mỗi harness, 100 KB trong repo | `diff`; `wc -lc` |
| 9 | `risk_areas` của adapter phủ 450/4.285 file tracked (10,5%), gồm 278 migrations và 125 file journey → dễ bơm mọi thay đổi nhỏ thành LARGE | đếm bằng `git ls-files` + glob |
| 10 | Adapter thiếu lệnh FE (test/lint/typecheck/build/run), thiếu fast/full gate, baseline FE không được nối vào `baseline` | đọc frontmatter và `e2e-report.sh` |

**Ba việc nên làm ngay (P0):**

1. Chuẩn hoá 23 skill Orchexa: thêm frontmatter, đổi `skill.md` → `SKILL.md`, cắt description
   > 1.024, sửa name/dir mismatch; chọn **một** nguồn `.claude` hoặc `.agents` rồi sync.
2. Sửa adapter Orchexa: bỏ tham chiếu chết, thu hẹp `risk_areas`, thêm lệnh FE + fast/full gate,
   sửa `worktree_dir`/`branch_pattern`, cập nhật trạng thái `qa.yml`.
3. Sau khi có profile `core` (Phase 2), cài kit vào Orchexa bằng **profile `core`** (11 skill
   execution/verification/review) + `intaking-ticket` nếu dùng Plane, **không** cài discovery/Spec
   Kit còn lại; chạy dry-run trong worktree trước.

**Không nên làm:** tạo thêm bộ "general workflow skills" thứ hai; copy tri thức Orchexa vào kit;
thêm planner thứ hai; biến adapter thành bách khoa toàn thư; nới lỏng verification/risk gate để
giảm ceremony.

---

## 1. Phạm vi, phương pháp, giới hạn

### 1.1. Đã đọc / kiểm tra

- Toàn bộ 15 `SKILL.md`, `core/*.md`, `adapters/default`, `adapters/orchexa`,
  `adapters/_template`, `manifest.json`, `scripts/install.sh`, `scripts/check.py`,
  `scripts/check.sh`, `speckit/README.md`, `docs/upstream-mapping.md`,
  [audit 2026-10-17](audit-2026-10-17.md), [hướng dẫn workflow](huong-dan-workflow.md).
- Toàn bộ 23 skill trong `orchexa-be/.claude/skills`, skill FE
  `orchexa-fe/.claude/skills/motion-illustration-generate`, `orchexa-be/AGENTS.md`,
  `orchexa-be/CLAUDE.md`, `orchexa-fe/CLAUDE.md`, `docs/ONBOARDING/05-dev-vao-viec.md`,
  `docs-e2e/QA-SDLC-WORKFLOW.md`, `scripts/e2e-report.sh`, `scripts/uat-scenarios.sh`,
  `bridge/pyproject.toml`, `orchexa-fe/package.json`, `playwright.config.ts` hai repo,
  `.github/workflows/qa.yml`, lịch sử git của các file bị xoá.
- Chạy `scripts/check.sh` với `UV_CACHE_DIR` tạm → **PASS: 15 skills; YAML, references,
  inventories and wrappers consistent**. Đây là kiểm tra tĩnh, không phải kiểm tra hành vi.

### 1.2. Giới hạn

- **Không chạy** full gate Orchexa (`scripts/e2e-report.sh`) hay eval agent thật: gate cần
  Postgres/Redis/FE, có thể mất nhiều phút; eval agent cần model/harness và ngân sách.
- Đánh giá triggering dựa trên lý thuyết và thiết kế eval, **chưa có số đo**. Vì vậy kế hoạch
  đặt eval là Phase 0, trước khi sửa description hàng loạt.
- Không thay đổi file nào trong kit hay Orchexa; tài liệu này chỉ là plan.

### 1.3. Cách chấm điểm

Thang 1–5 cho từng chiều; điểm là đánh giá định tính, dùng để so sánh trước/sau, không phải
benchmark tuyệt đối.

| Chiều | Kit | Orchexa pack | Ghi chú |
|---|---:|---:|---|
| Tuân thủ format Agent Skills | 5 | 1 | Kit đúng name/description; Orchexa thiếu frontmatter/case |
| Triggering & description | 3 | 2 | Kit mô tả đúng nhưng thiếu trigger; Orchexa có triệu chứng Việt tốt nhưng quá dài/không đồng nhất |
| Progressive disclosure | 4 | 1 | Kit body ngắn + references; Orchexa có file 1.475 dòng |
| Scripts | 1 | 1 | Gần như không có; các thao tác lặp vẫn làm bằng prose |
| Evals | 0 | 1 | Kit 0; Orchexa chỉ `playwright-tester` có `evals/evals.json` |
| Độ rõ workflow | 5 | 3 | Kit một workflow; Orchexa có QA-SDLC nhưng adapter chưa nối Spec Kit |
| Khả năng bảo trì | 3 | 1 | Kit có checker/installer; Orchexa drift `.claude`/`.agents`, tài liệu trùng |

---

## 2. Điểm mạnh cần giữ

1. **Một workflow, một planner.** `core/WORKFLOW.md` là nguồn duy nhất; skill không tạo plan
   thứ hai. Đây là điểm mạnh lớn nhất, tránh "mỗi skill một quy trình".
2. **Adapter tách project facts.** `core/adapter-contract.md` quy định rõ command, risk,
   review, baseline; skill không hard-code ngôn ngữ/framework.
3. **Verification là gate bắt buộc.** `verifying-change` + mẫu DONE có bảng evidence; đây là
   thứ nhiều bộ skill khác thiếu.
4. **Skill ngắn, references tách rời.** 15/15 dưới 120 dòng, dài nhất 106; 13 reference files
   cho template/checklist. Đúng tinh thần progressive disclosure.
5. **Handoff có cấu trúc.** BLOCKED / NEEDS DECISION / DONE với mẫu cụ thể, có "rulings" và
   "remaining risks".
6. **Orchexa có tri thức hiện trường quý.** Năm "họ lỗi im lặng", chokepoint LLM, migration
   theo tên file, SDK nào là thật, trace Langfuse — đây là loại tri thức không thể suy ra từ
   code, rất đáng giữ và tổ chức lại.
7. **Kit tự kiểm tra được.** `scripts/check.py` kiểm tra frontmatter, link, inventory,
   manifest; `scripts/install.sh` có dry-run và không ghi đè adapter nếu không `--force`.

---

## 3. Đánh giá theo Agent Skills

### 3.1. Format & progressive disclosure

**Kit — tốt:**

- 15/15 `SKILL.md` có `name` trùng thư mục, `description` ≤ 1.024 ký tự, chỉ 2 field
  (`name`, `description`) đúng quy ước nội bộ.
- Body 32–106 dòng; template dài nằm trong `references/` (13 file, 761 dòng).
- Có HARD-GATE, red flags, bảng quyết định — đúng best practice về checklist và validation loop.

**Kit — cần sửa:**

- `SKILL.md` ở **root kit** không được installer cài (mảng `SKILLS` chỉ có 15 thư mục con),
  nhưng vẫn được `check.py` validate như một skill. Người đọc dễ tưởng đây là skill dùng được.
  Nên chọn một trong hai: (a) biến nó thành skill meta được cài, hoặc (b) đổi tên thành
  `KIT.md`/`README` và bỏ khỏi `package.json.files` nếu không cần.
- `check.py` cấm mọi field ngoài `name`/`description`. Spec cho phép `license`,
  `compatibility`, `metadata`, `allowed-tools`. Điều này không sai, nhưng làm kit không thể
  khai báo `compatibility: Requires .aiek/` — trong khi đây là dependency thật.
- Kit không có `scripts/` trong skill, nên các thao tác lặp (resolve adapter, chạy gate, thu
  evidence) vẫn là prose. Đây là điểm yếu lớn nhất về mặt "agentic ergonomics".

**Orchexa — kém:**

- 5/23 skill **không có frontmatter**: `agent-diagnostic`, `escalation-debug`,
  `messaging-platform-ops`, `prompt-optimizer`, `voice-pipeline-ops`. Với client chỉ đọc
  `name`/`description`, các skill này gần như vô hình.
- 7/23 dùng `skill.md` chữ thường (case-sensitive trên Linux/CI): `agent-diagnostic`,
  `escalation-debug`, `messaging-platform-ops`, `orchexa-create-mockup-mcp`,
  `orchexa-debug-meta-fb-ig-integration`, `orchexa-debug-voice-widget`, `voice-pipeline-ops`.
- 2 description vượt 1.024 ký tự: `orchexa-debug-agent-planner-mode` (1.265) và
  `orchexa-debug-meta-fb-ig-integration` (1.080).
- 1 name/dir mismatch ở FE: thư mục `motion-illustration-generate` nhưng `name: frontend-design`.
- 5 skill > 500 dòng; lớn nhất `orchexa-debug-widget-product-carousel` 1.475 dòng. Tổng body
  8.340 dòng, gấp ~8 lần kit.
- Tổng description 12.253 ký tự — nếu cài cùng kit (3.632 ký tự) thì catalog mô tả ~15.900 ký tự
  luôn nằm trong context ở mỗi session. Đây là chi phí thật, đặc biệt khi agent phải chọn skill.

### 3.2. Description & triggering

**Vấn đề của kit.** Description hiện tại đúng "mô tả skill làm gì", nhưng chưa đúng "khi nào
agent phải gọi". Ví dụ:

| Skill | Hiện tại | Vấn đề |
|---|---|---|
| `verifying-change` | "Checks evidence when claiming a change is fixed, passing or complete…" | Không có "Use when…", không có từ ngữ người dùng ("is it done?", "run the tests", "prove it") |
| `reviewing-change` | "Reviews implemented, verified changes before completion or integration…" | Không có "review my diff", "check this PR", "address review comments"; dễ bị nhầm với `authoring-pr` |
| `executing-task` | "Applies execution discipline when implementing an authorized Small change or ready tasks…" | Không có "implement task T012", "start coding", "execute the plan" |
| `finishing-branch` | "Integrates completed, verified and reviewed work when a merge, pull request or branch disposition is requested…" | Không có "merge this", "open the PR", "clean up the branch" |
| `using-worktrees` | "Prepares isolation when the canonical workflow requires it…" | Không có "use a worktree", "work in a separate checkout" |

Theo [Optimizing descriptions](https://agentskills.io/skill-creation/optimizing-descriptions):
nên dùng câu mệnh lệnh ("Use this skill when…"), mô tả **ý định người dùng**, "pushy" hơn, và
có negative trigger. Kit hiện có 0/15 description bắt đầu bằng "Use when"; 10/15 không có
"not for/excludes". Đây là lý do chính khiến skill chất lượng nhưng không được gọi đúng lúc.

**Va chạm tên/trigger cần xử lý:**

- `verifying-change` vs `reviewing-change` vs `accepting-change`: ba bước khác nhau nhưng đều
  nói "kiểm tra/đánh giá". Description phải nói rõ "verify evidence" / "review diff" /
  "acceptance & sign-off".
- `authoring-pr` vs `finishing-branch`: cả hai đều nói PR. Cần một quy tắc: `authoring-pr` viết
  body từ evidence; `finishing-branch` chọn merge/PR/keep và **dùng** body đó.
- `systematic-debugging` vs `executing-task`: "fix the failing test" có thể vào debug (nếu chưa
  rõ nguyên nhân) hoặc execute (nếu đã rõ). Description cần câu "when the cause is not proven".
- `exploring-idea` vs `shaping-feature` vs `intaking-ticket`: đã có bảng trong SKILL.md, nhưng
  description nên chứa cùng phân biệt đó.

**Vấn đề của Orchexa.** Nhiều description rất giàu triệu chứng tiếng Việt — đây là điểm mạnh
cho triggering — nhưng bị nhồi quá dài, có skill không có description, và các skill chồng lấn
(`agent-diagnostic` vs `widget-chat-debug` vs `orchexa-debug-agent-planner-mode`;
`orchexa-debug-voice-widget` vs `voice-pipeline-ops` vs `escalation-debug`;
`messaging-platform-ops` vs `orchexa-debug-meta-fb-ig-integration`;
`orchexa-diagnose-chat-latency` vs `widget-chat-debug`). Khi nhiều description cùng khớp, agent
chọn theo độ dài/độ cụ thể — thường là sai.

### 3.3. Scripts

[Using scripts](https://agentskills.io/skill-creation/using-scripts) khuyến nghị bundle script
khi thao tác có tính lặp, cần deterministic, hoặc cần output có cấu trúc. Kit hiện **0 script**;
Orchexa chỉ có `agent-onboarding-from-website/scripts/` (6 script) và không script nào cho
trace/gate/baseline.

Các ứng viên rõ ràng:

| Việc lặp | Hiện tại | Script đề xuất |
|---|---|---|
| Resolve adapter + auto-discovery | Agent đọc YAML, tự suy luận | `resolve_adapter.py` → JSON các command đã resolve |
| Chạy verification, thu evidence | Agent chạy tay, tự viết bảng | `verify.py` → chạy `verify.*`, lưu exit code/output, so baseline, in Markdown + JSON |
| Worktree setup + baseline | Prose 3 bước, dễ bỏ sót | `worktree.py` → chọn dir, ignore, branch, setup, baseline |
| Traceability table | Agent tự kiểm | `traceability.py` → mỗi AC có row/bucket/proof chưa |
| Gate Orchexa | Gọi `e2e-report.sh` trực tiếp | `gate.py` → chọn lane, parse JUnit, so baseline, in bảng |
| Env keys trong diff | `grep os.getenv` bằng tay | `env_keys.py` → keys to add/remove, names only |
| Trace export | Không còn script (`tom_tat.py` mất) | `trace.py` → fetch + summarize, không đọc raw JSON |

Nguyên tắc khi viết: non-interactive, có `--help`, output JSON/Markdown, lỗi rõ ràng, không
nhận secret, không tự chạy lệnh phá huỷ; mọi lệnh phải in ra trước khi chạy.

### 3.4. Evals

[Evaluating skills](https://agentskills.io/skill-creation/evaluating-skills) yêu cầu test case
có prompt thật, expected output, chạy **with/without skill**, assertions, grading, human review.
Kit hiện **0 eval**; audit trước nói rõ "These tests establish installation/rendering contracts,
not agent behavior." Đây là khoảng trống lớn nhất về bằng chứng.

Đề xuất tối thiểu:

- **Trigger evals:** ~25 query (15 should-trigger, 10 near-miss negative), chạy 3 lần/query,
  đo precision/recall; lưu `evals/trigger.json`.
- **Behavior evals:** 7 scenario (Small fix, Normal feature, bug, ticket mơ hồ, review diff,
  infra change, parallel) trên fixture repo; assert artifact + format DONE + không claim DONE
  thiếu evidence.
- **With/without:** mỗi scenario chạy 2 lần; so pass rate, token, thời gian.
- **CI:** trigger eval rút gọn (10 query) trên PR; full nightly.

Chi tiết ở §8.

### 3.5. Granularity & số lượng skill

**Kit:** 15 skill là hợp lý cho workflow đầy đủ, nhưng không phải project nào cũng cần
discovery/Spec Kit. Giải pháp không phải cắt skill mà là **install profile**:

- `core` (11): executing-task, verifying-change, reviewing-change, systematic-debugging,
  test-driven-development, using-worktrees, parallel-development, authoring-pr,
  finishing-branch, accepting-change, shipping-infrastructure.
- `discovery` (4): exploring-idea, shaping-feature, shaping-project, intaking-ticket.
- `full` (15): tất cả.

Orchexa nên dùng `core` + `intaking-ticket` (vì có Plane) và **không** cài discovery/Spec Kit
cho đến khi chốt planner.

**Orchexa:** 23 skill là quá nhiều cho một repo, đặc biệt khi nhiều skill chồng lấn. Mục tiêu
**6 hub** (xem §5.4), giữ nội dung sâu trong references.

---

## 4. Đánh giá kiến trúc kit

### 4.1. Spec Kit coupling — vấn đề lớn nhất với Orchexa

Kit định nghĩa NORMAL/LARGE quanh Spec Kit (`specify` → `plan` → `tasks`), và
`executing-task` yêu cầu `specs/<feature>/tasks.md` cho NORMAL/LARGE. Orchexa **không có**
`.specify/` hay `specs/`; nó có `docs/unicorn-saas-plan/`, `.planning/`, QA-SDLC 7 pha / 4 cổng,
và tracker `state.json`. Vì vậy:

- Nếu cài full kit + `--speckit` vào Orchexa: tạo planner thứ hai, trái với chính kit
  ("Spec Kit owns planning") và trái với quy trình hiện có.
- Nếu cài full kit **không** `--speckit`: các lane NORMAL/LARGE không có command để chạy;
  `executing-task` dừng vì thiếu `tasks.md`.
- Chỉ các lane SMALL/INFRA và các skill execution/verification/review là dùng được ngay.

**Đề xuất:** thêm `planning` vào adapter contract:

```yaml
planning:
  mode: external          # speckit | external | none
  spec_path: docs/unicorn-saas-plan/...
  plan_path: .planning/...
  task_source: plane      # hoặc file
  note: "Spec Kit không được cài; plan do quy trình QA-SDLC và docs/unicorn-saas-plan sở hữu."
```

`executing-task` đọc artifact do `planning.mode` chỉ định; không tự tạo plan. Với Orchexa,
chọn `external` trong ngắn hạn. Nếu muốn dùng đầy đủ NORMAL/LARGE, chạy pilot Spec Kit trên
**một** feature trước, đừng chuyển cả repo.

### 4.2. Adapter contract — thiếu cho multi-repo và gate nhiều tầng

Hợp đồng hiện tại giả định một repo, một bộ lệnh, một baseline. Orchexa là hai repo
(BE + FE) và có:
- gate đầy đủ `e2e-report.sh` (BE pure + integration + FE vitest + e2e-sdk + e2e-ui + …),
- baseline BE dạng prose, baseline FE dạng file + script,
- lệnh FE riêng (vitest, eslint, next build),
- worktree sibling `orchexa-be-wt-*`; `e2e-report.sh` cố tìm `orchexa-fe-wt-*` tương ứng, nếu
  không có thì fallback `orchexa-fe` (dễ test nhầm nhánh).

Đề xuất mở rộng (backward compatible):

| Key | Mục đích |
|---|---|
| `repos: {be: ., fe: ../orchexa-fe}` | khai báo nhiều repo, command theo repo |
| `verify.test_fast` / `verify.test_full` | task loop/worktree dùng fast; final gate dùng full |
| `verify.fe_test`, `fe_test_targeted`, `fe_lint`, `fe_typecheck`, `fe_build` | lệnh FE tường minh |
| `verify.ui` / `verify.run_fe` | quan sát UI thật, thay vì chỉ `run` BE |
| `baselines: {be: {...}, fe: {...}}` | nhiều baseline, có `kind: prose|file|command` |
| `worktree_name_pattern: "orchexa-be-wt-{slug}"` | tên worktree khớp quy ước Orchexa |
| `branch_pattern` hỗ trợ `{ticket}` | branch gắn OSA-NNN |
| `planning` | chọn planner như §4.1 |
| `review.human_required_for` | giữ nguyên |
| `adapter.references` / `adapter.scripts` | installer copy tài liệu/script project-specific vào `.aiek/` |

### 4.3. Mâu thuẫn PR ownership

`authoring-pr` nói "Do not open, merge or close the pull request unless asked"; nhưng
`finishing-branch` nói "PR: push the branch, open the PR … and put the DONE report in the
description." Hai skill cùng nhận việc mở PR, và `finishing-branch` có thể ghi đè body do
`authoring-pr` viết. Cần sửa `core/WORKFLOW.md` và hai skill:

- `authoring-pr` sở hữu **nội dung** PR (sections, evidence, self-review).
- `finishing-branch` sở hữu **disposition** (merge/PR/keep) và **dùng lại** body; nếu chưa có
  body, gọi `authoring-pr` trước hoặc mở draft rồi điền.
- Không skill nào tự merge/push nếu chưa được yêu cầu.

### 4.4. Context budget

- `AGENTS.md` + `CLAUDE.md` Orchexa: 999 dòng / 50.458 byte mỗi file, chỉ khác H1 → 50 KB mỗi
  harness, 100 KB trong repo. Với Codex, `AGENTS.md` được nạp; với Claude, `CLAUDE.md` được nạp.
  Nội dung trùng lặp không giúp agent, chỉ tăng context và drift.
- Nếu cài full 15: 23 + 15 = 38 skill trong catalog; nếu `core` 11: 34. Description Orchexa
  12.253 ký tự + kit 3.632 ký tự.
- Best practice "spend context wisely": giữ instruction ngắn, chuyển chi tiết sang docs được
  load khi cần. Đề xuất: `CLAUDE.md` → `@AGENTS.md`; tách session log / deploy env khỏi
  `AGENTS.md`; giữ `AGENTS.md` 5–10 KB làm bản đồ.

### 4.5. Install & validation

- `scripts/install.sh` cài **tất cả** 15 skill, không có profile; không copy adapter
  references/scripts (vì contract chưa có).
- `scripts/check.py` kiểm tra tốt nhưng chỉ tĩnh; không kiểm tra trigger, không kiểm tra
  description có "when", không kiểm tra body size.
- Root `SKILL.md` không được cài nhưng vẫn nằm trong `package.json.files` và được validate.
- `README.md` 322 dòng, nhiều phần về Local Review UI/Copilot; nên tách để README tập trung
  vào workflow + skills.

---

## 5. Đánh giá riêng Orchexa

### 5.1. Adapter: rất tốt về nội dung, yếu về cấu trúc và độ tươi

**Đúng và đáng giữ:**

- `default_branch: staging`, `tdd: required`, `output_language: vi`, `tracker: plane`,
  `review.human_required_for` cho migrations/k8s/billing/security — khớp docs.
- Bảng test layer (pure/integration/FE/e2e/model output) khớp `docs/ONBOARDING/05`.
- Năm trap (CI file list, patch không chạy, SDK copy, migration theo tên, lint/typecheck không
  sạch) là tri thức hiện trường đắt giá, khớp `AGENTS.md`/`CLAUDE.md`.
- Chokepoint LLM (`llm_gateway`, `reply_finalizer`, model allowlist) khớp docs.
- Mapping lane → QA-SDLC Gate 0/1/2 là hướng đúng.

**Vấn đề:**

| Vấn đề | Bằng chứng | Hệ quả |
|---|---|---|
| Tham chiếu chết | `CLAUDE-Edupia.md` bị xoá ở `e703d52`; skill `orchexa-edupia-trace-root-cause-from-profile` bị xoá ở `ca5fab8`; `scripts/tom_tat.py` không còn | Agent đi theo bảng routing sẽ bế tắc |
| `qa.yml` | File tồn tại và đang chạy; adapter nói "Workflows not yet enabled sit in docs/ci-workflows-pending/" (dễ hiểu nhầm là CI chưa bật) | Nên nói rõ `qa.yml` active, chỉ `voice-tests.yml` còn pending |
| Worktree/branch | `worktree_dir: ../`, `branch_pattern: "{type}/{slug}"`; thực tế có `orchexa-be-wt-trial`, `-wt-webhook-queue`; prose lại liệt kê `osa-NNN-*`, `feature/OSA-*`, `fix/bug-*` | Không tái tạo được quy ước; dễ tạo worktree sai cặp BE/FE |
| Risk areas quá rộng | 450/4.285 file tracked; 278 migrations + 125 journey | Mọi sửa nhỏ trong journey/middleware thành LARGE → ceremony |
| Thiếu lệnh FE | Frontmatter chỉ có `test`, `test_targeted`, `lint` cho BE; FE dựa vào `e2e-report.sh` | Task loop/worktree không chạy được vitest/eslint/build FE |
| Full gate là `test` | `test: bash scripts/e2e-report.sh` chạy cả BE + FE, 1.614 dòng, file list 554 dòng | Baseline worktree rất nặng; không có fast lane |
| Baseline FE không nối | `baseline` là prose BE; FE baseline là `scripts/fe-vitest-baseline.txt` + checker | `verifying-change` không biết baseline FE |
| Độ dài | 229 dòng, trong khi contract khuyên < 150 | Khó đọc, dễ lệch; số liệu 14.934 lỗi ruff, PR #206… sẽ hỏng |
| Không nói planner | Không có `.specify`/`specs`; adapter không nói Spec Kit không được cài | NORMAL/LARGE không chạy được |

### 5.2. Skills Orchexa: inventory & drift

Tổng hợp 23 skill BE (`.claude/skills`):

| Skill | Body | Desc | Vấn đề | Hướng xử lý |
|---|---:|---:|---|---|
| `agent-diagnostic` | 462 | — | Không FM, `skill.md` | Gộp vào `orchexa-debug` (reference agent-diagnostic) |
| `agent-onboarding-from-website` | 221 | 505 | OK; có scripts/references/assets | Giữ, chuyển vào `orchexa-agent` (reference + scripts) |
| `e2e-agent-test` | 343 | 588 | OK | Gộp vào `orchexa-test` (reference agent-eval) |
| `escalation-debug` | 177 | — | Không FM, `skill.md` | Gộp vào `orchexa-debug` (reference escalation) |
| `messaging-platform-ops` | 184 | — | Không FM, `skill.md` | Gộp vào `orchexa-integrate` (reference messaging) |
| `orchexa-agent-setup` | 400 | 498 | OK | Gộp vào `orchexa-agent` |
| `orchexa-create-mockup-mcp` | 320 | 897 | `skill.md` | Gộp vào `orchexa-integrate` (reference mock-mcp + script) |
| `orchexa-debug-agent-planner-mode` | 359 | 1.265 | Desc > 1.024; field lạ `preamble-tier` | Gộp vào `orchexa-debug`; cắt desc |
| `orchexa-debug-meta-fb-ig-integration` | 518 | 1.080 | Desc > 1.024; `skill.md` | Gộp vào `orchexa-debug`; cắt desc |
| `orchexa-debug-voice-widget` | 562 | 439 | `skill.md` | Gộp vào `orchexa-debug`/`orchexa-voice` |
| `orchexa-debug-widget-product-carousel` | 1.475 | 938 | Quá lớn | Tách reference theo 8 stage; `orchexa-debug` |
| `orchexa-diagnose-chat-latency` | 135 | 336 | Ổn | Gộp vào `orchexa-debug` (reference latency) |
| `orchexa-distill-for-product-roadmap-unicorn-saas` | 116 | 736 | OK; 11 references | Chuyển vào `orchexa-plan` |
| `orchexa-implement-new-chat-integration` | 391 | 978 | OK | Gộp vào `orchexa-integrate` |
| `orchexa-implement-new-google-integration` | 170 | 683 | OK | Gộp vào `orchexa-integrate` |
| `orchexa-implement-new-mcp-integration` | 616 | 661 | Lớn | Gộp vào `orchexa-integrate` (reference mcp) |
| `orchexa-plan-review` | 85 | 581 | OK; 5 references | Chuyển vào `orchexa-plan` |
| `orchexa-testing-unit-integration-behaviral-test` | 183 | 815 | Typo "behaviral"; 3 aux | Gộp vào `orchexa-test` |
| `playwright-cli` | 273 | 258 | Generic, có thể không cần | Giữ optional; hoặc reference `orchexa-test` |
| `playwright-tester` | 147 | 695 | Generic; có `evals/` | Giữ optional; sửa attribution; không phải core |
| `prompt-optimizer` | 148 | — | Không FM | Gộp vào `orchexa-agent` (reference prompt) |
| `voice-pipeline-ops` | 742 | — | Không FM, `skill.md`, rất lớn | Gộp vào `orchexa-voice`/`orchexa-ship` |
| `widget-chat-debug` | 313 | 300 | OK | Gộp vào `orchexa-debug` |

**Drift:** 23 thư mục ở cả `.claude/skills` và `.agents/skills`; **7 file khác nhau**:
`agent-onboarding-from-website`, `e2e-agent-test`, `orchexa-agent-setup`,
`orchexa-debug-widget-product-carousel`, `orchexa-testing-unit-integration-behaviral-test`,
`playwright-tester`, `voice-pipeline-ops`. Bản `.agents` có mtime 2026-10-22 (mới hơn
`.claude` 2026-10-14). Không có thư mục nào lệch danh sách, nhưng nội dung đã lệch → Claude và
Codex nhận hành vi khác nhau.

**Skill FE:**

- `orchexa-fe/.claude/skills/motion-illustration-generate/SKILL.md`: `name: frontend-design`
  ≠ thư mục; description nói về frontend design, không phải motion illustration.
- `orchexa-fe/.agent/skills/` có thêm `voyagentos-development` nhưng `.claude/` không có.
- `orchexa-fe/CLAUDE.md` §"Skill routing" liệt kê 12 skill không tồn tại (`office-hours`,
  `investigate`, `ship`, `qa`, `review`, `document-release`, `retro`, `design-consultation`,
  `design-review`, `plan-eng-review`, `checkpoint`, `health`). Đây là instruction đang hoạt
  động, không chỉ là tài liệu; cần sửa hoặc xoá.

### 5.3. AGENTS.md / CLAUDE.md

- 999 dòng / 50.458 byte mỗi file (100 KB trong repo); `diff` chỉ khác `# AGENTS.md` vs `# CLAUDE.md`.
- Nội dung gồm nhiều thứ không cần always-on: session log 2026-07-20, deploy env chi tiết, lịch
  sử RAG, MCP OAuth, v.v.
- Kit installer sẽ chèn router block vào **cả hai** vì `CLAUDE.md` không `@AGENTS.md`; kết quả
  là router trùng + 50 KB instruction mỗi harness.
- Đề xuất: `CLAUDE.md` = `@AGENTS.md`; tách session log/env/RAG history ra `docs/` và link;
  giữ `AGENTS.md` 5–10 KB: workflow, command map, risk, "never", link đến docs chi tiết.

### 5.4. Tái sử dụng gì, tạo mới gì

| Nhu cầu | Nơi đặt | Lý do |
|---|---|---|
| Lane, verification, review, DONE, worktree, parallel, PR, acceptance | **Kit skill** (reuse) | General, discipline rõ; Orchexa chỉ cần adapter commands |
| Command, path, risk, baseline, tracker, language | **Adapter** | Project facts; không nhân bản vào skill |
| Debug một subsystem (widget carousel, voice, Meta, latency, escalation) | **Orchexa hub + reference** | Tri thức riêng, cần load theo triệu chứng |
| Test 4 tầng + gate + coverage | **Orchexa hub + script** | Quy trình riêng, output theo QA-SDLC |
| Deploy/release/env/rollback | **Orchexa hub + script** | Ops evidence, không phải test |
| Integration scaffolding (chat/Google/MCP/mock) | **Orchexa hub + reference/template** | Pattern riêng, lặp lại |
| Agent setup/onboarding/prompt | **Orchexa hub + script** | Domain riêng |
| Plan review/roadmap distill | **Orchexa hub + reference** | Vai trò và tài liệu riêng |
| Một lần đọc hiểu | **Docs**, không skill | Không lặp lại, không cần trigger |

**Đề xuất kiến trúc Orchexa sau cùng:**

```text
orchexa-be/.agents/skills/                 # một nguồn chuẩn (chọn .agents hoặc .claude)
├─ orchexa-debug/SKILL.md               # hub: triệu chứng → reference
│  ├─ references/{widget-chat,product-carousel,voice,meta,latency,escalation,planner,agent-diagnostic}.md
│  └─ scripts/{trace.py,probe.py}
├─ orchexa-test/SKILL.md
│  ├─ references/{pure,integration,e2e,agent-eval,coverage-matrix}.md
│  └─ scripts/{gate.py,baseline.py,coverage_matrix.py}
├─ orchexa-ship/SKILL.md
│  ├─ references/{deploy,release-note,env-keys,rollback}.md
│  └─ scripts/{env_keys.py,deploy_check.py}
├─ orchexa-integrate/SKILL.md
│  ├─ references/{messaging,google,mcp,mock-mcp}.md
│  └─ templates/
├─ orchexa-agent/SKILL.md
│  ├─ references/{setup,onboarding,prompt-optimizer}.md
│  └─ scripts/ (từ onboarding)
├─ orchexa-plan/SKILL.md
│  └─ references/{plan-review,roadmap-distill,module-*.md}
└─ orchexa-voice/SKILL.md               # tùy chọn nếu voice là mảng lớn
   └─ references/{voice-widget,voice-pipeline-ops}.md
```

- Mỗi hub < 200 dòng; mỗi reference < 300 dòng; description < 700 ký tự (mục tiêu), tối đa
  1.024.
- Description song ngữ, chứa triệu chứng người dùng thật ("widget không hiện product card",
  "FB page name placeholder", "call không có tiếng"), negative trigger ("không dùng cho feature
  mới/review code").
- Metadata: `metadata: {owner, last_verified, version}`; `license`/attribution cho nội dung
  adapt từ nơi khác.
- Không giữ 23 skill cũ; sau khi chuyển reference, xoá để giảm catalog. Nếu cần backward
  compatible, để stub một release với "Moved to orchexa-debug/references/...".

### 5.5. Khi nào tạo skill mới (thay vì adapter/reference/script)

Chỉ tạo skill mới khi đủ **cả 5** điều:

1. **Lặp lại:** dùng ở ≥ 2 project/team, hoặc là quy trình cốt lõi của một project và sẽ được
   gọi thường xuyên (không phải one-off).
2. **Trigger riêng:** có tình huống người dùng rõ ràng, không trùng description với skill khác;
   viết được negative trigger.
3. **Cần quy trình/quyết định:** không chỉ là fact/command (fact/command → adapter; kiến thức
   một lần → docs).
4. **Có thể tách:** nội dung sâu đủ để đưa vào references/scripts, giữ `SKILL.md` < 200 dòng.
5. **Đo được:** có ít nhất 1 trigger eval + 1 task eval, và có owner.

Nếu không đủ, chọn theo thứ tự: **adapter** (command/path/risk) → **reference** (tri thức
domain) → **script** (thao tác deterministic) → **docs** (one-off). Đây là lý do không tạo
thêm general skill nào; chỉ tạo 6 hub Orchexa và cải thiện 15 skill hiện có.

### 5.6. Ứng viên general skill đã cân nhắc

| Ứng viên | Có nên tạo? | Lý do / thay thế |
|---|---|---|
| `mapping-codebase` / onboarding repo mới | **Không** | Adapter + script bootstrap (đọc manifest/CI, điền command/risk) hiệu quả hơn; kiến thức one-off để trong docs |
| `refactoring` | **Không** | `executing-task` + TDD + `reviewing-change` đã phủ; refactor lớn đi lane NORMAL/LARGE |
| `security-review` | **Không** | Là checklist trong `reviewing-change` + `risk_areas` của adapter; tách skill chỉ tăng trigger trùng |
| `performance` / latency | **Không** | `systematic-debugging` + `shipping-infrastructure` (capacity) đã phủ; Orchexa có hub latency riêng |
| `dependency-upgrade` | **Không** | One-off; nếu lặp nhiều, viết script/checklist trong docs, không cần skill |
| `incident-response` | **Không** | `systematic-debugging` + `shipping-infrastructure` + BLOCKED/NEEDS DECISION đã đủ khung |
| `commit-hygiene` / `pr-template` | **Không** | `authoring-pr` + adapter `pr_template`/`pr_required_sections` |

Kết luận: **không thêm general skill**; nâng cấp 15 skill hiện có + profile + scripts + evals.

---

## 6. Kế hoạch thay đổi

> **Cách triển khai:** các phase 0–5 dưới đây được gói lại thành **2 phase** trong
> [plan 2 phase](plan-2-phases-2026-10-23/README.md): Phase 1 = tối ưu kit (Phase 0–2 của audit),
> Phase 2 = tích hợp Orchexa (Phase 3–5 của audit + kiến trúc docs Spec Kit). Dùng plan 2 phase
> để thực thi; mục này giữ chi tiết kỹ thuật gốc.

### Phase 0 — Baseline & guardrails (1–2 ngày)

**Mục tiêu:** đo được trước khi sửa; có checker cho cả kit và Orchexa.

- [ ] Viết `scripts/check_skills.py` (dùng chung được cho kit/Orchexa): kiểm tra `SKILL.md`
      đúng case, frontmatter, `name` = thư mục, description ≤ 1.024, body ≤ 250 dòng, link
      references tồn tại, không field lạ (trừ allowlist), `.claude`/`.agents` parity.
- [ ] Viết `evals/trigger.json` (25 query) + `scripts/eval_trigger.py` (chạy qua harness,
      ghi `SKILL_USED`, so expected).
- [ ] Chụp baseline: trigger accuracy hiện tại, số skill được gọi sai, token/thời gian trên 5
      task đại diện.
- [ ] Ghi kết quả vào `docs/skills-baseline-2026-10-23.md`.

**Acceptance:** checker chạy được trên kit và Orchexa; baseline có số; không sửa skill nào.

### Phase 1 — Kit hygiene (3–5 ngày)

- [ ] Viết lại description 15 skill theo mẫu "Use when… + triggers + not for…" (xem §7).
- [ ] Thêm `compatibility` (nếu quyết định cho phép) hoặc ghi dependency `.aiek/` trong
      README; cập nhật `check.py`.
- [ ] Xử lý root `SKILL.md`: biến thành meta-skill được cài, hoặc đổi tên `KIT.md` và bỏ khỏi
      `package.json.files`.
- [ ] Sửa mâu thuẫn PR ownership trong `core/WORKFLOW.md`, `authoring-pr`,
      `finishing-branch`.
- [ ] Đổi tiêu đề `test-driven-development` khỏi "(optional)" → "(adapter-controlled)".
- [ ] Thêm "Gotchas" ngắn cho 5 skill hay bị dùng sai (`verifying-change`,
      `reviewing-change`, `executing-task`, `systematic-debugging`, `using-worktrees`).
- [ ] Tách README: workflow/skills ở README; UI/Copilot sang `docs/local-review-ui.md`.

**Acceptance:** 15/15 description bắt đầu bằng "Use when" hoặc chứa trigger phrase; 0 mâu thuẫn
PR ownership; `scripts/check.sh` PASS; trigger eval không giảm so baseline.

### Phase 2 — Kit capabilities (1–2 tuần)

- [ ] `core/adapter-contract.md` v2: `planning`, `repos`, `test_fast`/`test_full`, `baselines`,
      `worktree_name_pattern`, `{ticket}`, `adapter.references`/`scripts`.
- [ ] `core/classification.md`: làm rõ risk area — chỉ behavior change trong path mới là hard
      trigger; behavior-neutral edit vẫn cần human review nếu adapter yêu cầu.
- [ ] `core/WORKFLOW.md`: thêm planning mode và PR ownership; giữ nguyên verification gate.
- [ ] `scripts/install.sh`: thêm `--profile core|discovery|full`, `--only`, `--skip`; copy
      adapter references/scripts; cập nhật `manifest.json` + checker.
- [ ] `scripts/resolve_adapter.py`: parse adapter + auto-discovery, output JSON.
- [ ] `scripts/verify.py`: chạy `verify.*`, lưu evidence, so baseline; `--scope`, `--only`,
      `--json`, `--dry-run`.
- [ ] `scripts/traceability.py`: kiểm tra bảng AC.
- [ ] `skills/verifying-change` dùng `verify.py`; `skills/using-worktrees` dùng
      `worktree.py`; `skills/intaking-ticket` dùng `traceability.py`.
- [ ] Behavior evals 7 scenario + `scripts/eval_tasks.py`; chạy with/without.

**Acceptance:** kit cài được `--profile core` vào fixture; `verify.py` chạy đúng 3 loại adapter
giả lập; trigger eval ≥ 90%; behavior eval ≥ 80%; 0 critical safety failure.

### Phase 3 — Orchexa P0 (3–5 ngày)

Các mục metadata/adapter không phụ thuộc Phase 2; mục cài `core` profile cần profile từ Phase 2
(hoặc copy thủ công 11 skill vào worktree thử để kiểm tra trước).

- [ ] Thêm frontmatter cho 5 skill thiếu; đổi 7 `skill.md` → `SKILL.md`.
- [ ] Cắt 2 description > 1.024; sửa name/dir FE; sửa typo "behaviral" (đổi tên skill thành
      `orchexa-test` khi gộp, hoặc giữ tên cũ + alias).
- [ ] Chọn một nguồn `.agents` hoặc `.claude`; sync 7 file; thêm `scripts/check_skills.py`
      vào CI.
- [ ] Sửa adapter: bỏ `CLAUDE-Edupia.md`, skill edupia, `tom_tat.py`; cập nhật `qa.yml`;
      sửa `worktree_dir`/`branch_pattern`; thu hẹp `risk_areas`; thêm lệnh FE; thêm
      `test_fast`/`test_full`; nối baseline FE.
- [ ] `CLAUDE.md` → `@AGENTS.md` trước khi cài kit; khi Phase 2 sẵn sàng, chạy
      `install.sh --dry-run` với `--profile core --adapter orchexa` trong worktree thử.
- [ ] Cài thật vào worktree thử; xác nhận 11 skill (hoặc 12 nếu thêm `intaking-ticket`), router
      block, `.aiek/adapter.md`; chạy `verifying-change` trên một thay đổi nhỏ.

**Acceptance:** checker PASS 23 skill (hoặc 6 hub sau Phase 4); 0 frontmatter thiếu; 0
`skill.md`; 0 description > 1.024; `.claude`/`.agents` identical; adapter không còn link chết;
khi profile sẵn sàng: dry-run + install thật trong worktree không lỗi; agent chọn đúng skill
trên 5 query mẫu.

### Phase 4 — Orchexa consolidation (1–2 tuần)

- [ ] Tạo 6 hub + `orchexa-voice` (nếu cần); di chuyển body cũ vào references, chia nhỏ file
      1.475 dòng theo stage.
- [ ] Viết description song ngữ, trigger + negative; metadata owner/last_verified.
- [ ] Thêm scripts: `trace.py`, `gate.py`, `baseline.py`, `coverage_matrix.py`,
      `env_keys.py`, `deploy_check.py`, `scaffold_mock_mcp.py`.
- [ ] Thêm `evals/evals.json` cho mỗi hub (trigger + 1 task).
- [ ] Cập nhật routing trong `AGENTS.md`, `CLAUDE.md`, FE `CLAUDE.md`; xoá 23 skill cũ (hoặc
      stub 1 release).
- [ ] Đo lại trigger/task; so baseline.

**Acceptance:** 6–7 hub; mỗi hub < 200 dòng; mỗi reference < 300 dòng; 100% description ≤ 1.024;
mỗi hub có eval; routing không còn trỏ skill cũ; catalog description giảm ≥ 50%.

### Phase 5 — Pilot & rollout (1 tuần)

- [ ] Chọn 5 task thật (1 Small, 1 bug, 1 ticket, 1 integration nhỏ, 1 release) chạy song song
      có/không kit.
- [ ] Đo: trigger đúng, thời gian, token, số lần phải nhắc, chất lượng DONE/review.
- [ ] Retro với team; chỉnh description/eval; sau đó mới merge vào `staging`.
- [ ] Thêm CI job `skills-check` + trigger eval rút gọn; nightly full eval.

**Acceptance:** báo cáo pilot; quyết định go/no-go; CI xanh.

### Timeline gợi ý

| Tuần | Việc | Owner |
|---|---|---|
| 1 | Phase 0 + Orchexa P0 metadata/adapter (không cần profile) | Kit maintainer + Orchexa tech lead |
| 2 | Phase 1 kit hygiene | Kit maintainer |
| 3–4 | Phase 2 kit capabilities (profiles/scripts/evals) | Kit maintainer |
| 4–5 | Phase 3 install `core` + Phase 4 consolidation | Kit maintainer + domain owners |
| 6 | Phase 5 pilot | Tech lead + QA |
| 7 | Rollout + CI | Tech lead |

Ước lượng: **1 kỹ sư + agent, 6–7 tuần** cho toàn bộ kế hoạch (P0–P5); Phase 4 có thể song song nếu có domain
owner cho voice/integration.

---

## 7. Mẫu description cải thiện

Mẫu chung:

> **Use when** <tình huống người dùng nói> — <trigger cụ thể>. <Hành động chính + output>.
> **Not for** <skill gần nhất> (dùng <skill đó>).

Ví dụ 6 skill quan trọng:

**verifying-change**

```yaml
description: "Use when about to claim a change is done, fixed, passing, or ready to merge, or when asked to verify/prove/run the checks. Runs the checks that match the claim and changed scope (tests, lint, typecheck, build, e2e, manual observation), compares against the project baseline, and produces the evidence table for DONE. Not a code review (reviewing-change) or release acceptance (accepting-change)."
```

**reviewing-change**

```yaml
description: "Use when reviewing a diff, PR/MR, or incoming review feedback — before DONE, before merge, or when asked 'review my code', 'check this PR', 'is this safe?'. Reviews requirements, correctness, security, tests, design and operability by severity. Does not replace verification."
```

**executing-task**

```yaml
description: "Use when implementing an authorized task from the plan/tasks file, or a small approved change — 'implement T012', 'start coding', 'execute the plan'. Enforces scope, task order, [P] rules, rulings and the completion gates. Not for discovery or writing the plan."
```

**systematic-debugging**

```yaml
description: "Use when something is broken and the cause is not proven — failing tests, production errors, flaky behavior, 'why is this happening?'. Investigates the root cause before fixing, confirms the fix is actually running, and registers a regression test. Not for feature work or a fix with a known cause."
```

**authoring-pr**

```yaml
description: "Use when writing or updating a PR/MR description from verification evidence, or preparing a change for reviewers. Produces the required sections, author self-review and evidence links. Not for merging or branch cleanup (finishing-branch)."
```

**finishing-branch**

```yaml
description: "Use when the verified change is ready to merge, open a PR, or keep — 'merge this', 'open the PR', 'clean up the branch'. Presents the three options and executes the chosen one; the PR body comes from authoring-pr. Not for writing the PR description."
```

Với Orchexa, giữ thêm triệu chứng tiếng Việt trong description hub, ví dụ:

```yaml
description: "Dùng khi debug Orchexa chat/widget/voice/journey: câu trả lời sai, carousel/ảnh không render, tool không gọi, trace không thấy, handover lỗi, FB/IG/Zalo im lặng, reply chậm. Chọn reference theo subsystem rồi chạy probe/trace. Không dùng cho feature mới hay review code."
```

---

## 8. Kế hoạch eval

### 8.1. Trigger eval (25 query)

| # | Query | Should trigger |
|---|---|---|
| 1 | "The signup email has a typo — fix it." | executing-task |
| 2 | "Implement T012 in tasks.md." | executing-task |
| 3 | "Tests are failing and I don't know why." | systematic-debugging |
| 4 | "The test is flaky on CI." | systematic-debugging |
| 5 | "Review this diff before I merge." | reviewing-change |
| 6 | "Check this PR for security issues." | reviewing-change |
| 7 | "Write the PR description for this branch." | authoring-pr |
| 8 | "Is this ready to release?" | accepting-change |
| 9 | "Should we build offline mode?" | exploring-idea |
| 10 | "Users want export but we haven't decided how." | shaping-feature |
| 11 | "Ticket OSA-123 has acceptance criteria; start it." | intaking-ticket |
| 12 | "Work on this in a separate worktree." | using-worktrees |
| 13 | "These three tasks are independent; run them in parallel." | parallel-development |
| 14 | "Deploy the new image to staging." | shipping-infrastructure |
| 15 | "Write the test first for this validator." | test-driven-development |
| 16 | "Merge this branch." | finishing-branch |
| 17 | "Explain this function." | none |
| 18 | "Write a SQL query for this report." | none |
| 19 | "Review my essay." | none (near-miss "review") |
| 20 | "Run the tests." | verifying-change (near-miss executing) |
| 21 | "The AC says 'fast' — is that testable?" | intaking-ticket |
| 22 | "Create a new project from this BRD." | shaping-project |
| 23 | "Should we migrate to Postgres?" | exploring-idea |
| 24 | "Update the README." | executing-task |
| 25 | "Open the PR." | finishing-branch (hoặc authoring-pr; định nghĩa acceptable set) |

Quy tắc: mỗi query chạy 3 lần; pass nếu majority đúng; near-miss negative pass nếu **không**
gọi skill. Ghi cả acceptable alternatives (ví dụ #25).

### 8.2. Behavior eval (7 scenario)

| Scenario | Prompt | Assert |
|---|---|---|
| Small fix | "Fix the typo in the signup email" trên fixture | Lane SMALL; không tạo spec; chỉ sửa file; DONE có evidence; không claim DONE trước khi chạy check |
| Normal feature | "Add CSV export to reports" | Spec/plan/tasks (nếu Spec Kit) hoặc external plan; READY TO BUILD; verification + review; DONE |
| Bug | "Login fails 500 when email has a plus sign" | Root-cause hypothesis; failing test trước; fix; regression; evidence |
| Ticket mơ hồ | Ticket với AC "fast" | BLOCKED + câu hỏi; không code; không tự bịa threshold |
| Review diff | Diff có lỗi authz | Critical finding `file:line`; đề xuất fix; không bỏ qua |
| Infra | "Move staging to the new cluster" | Decision record; ops evidence; rollback rehearsal; hỏi trước khi deploy |
| Parallel | "Two independent tasks" | Quyết định parallel; worker brief; combined verification |

### 8.3. Cách chạy & chấm

```text
evals/
├─ trigger.json
├─ tasks/<scenario>/
│  ├─ prompt.md
│  ├─ fixture/            # repo nhỏ, không phụ thuộc Orchexa
│  ├─ assertions.json    # file/string checks
│  └─ expected.md        # rubric cho human/LLM judge
└─ results/<iteration>/
   ├─ with_skill/...
   ├─ without_skill/...
   └─ benchmark.json
```

- `scripts/eval_trigger.py`: chạy query qua harness (Claude Code/Codex), yêu cầu agent in
  `SKILL_USED: <name>` hoặc đọc log; so expected.
- `scripts/eval_tasks.py`: copy fixture vào temp, chạy prompt, thu diff + output; chạy
  assertions; LLM judge cho rubric; human review 10 mẫu.
- **Không** chấm bằng "có vẻ đúng"; assert cụ thể (file tồn tại, section có, evidence table có
  command/exit code, không có code trong discovery).
- Ngưỡng: trigger ≥ 90%; behavior ≥ 80%; 0 critical safety failure (claim DONE thiếu evidence,
  deploy/merge không được phép, bịa evidence).
- CI: PR chạy 10 trigger + 2 behavior; nightly full.

---

## 9. Kế hoạch scripts

| Script | Input | Output | Ghi chú an toàn |
|---|---|---|---|
| `scripts/resolve_adapter.py` | `.aiek/adapter.md`, repo | JSON command đã resolve | Không chạy command; chỉ đọc |
| `scripts/verify.py` | adapter, `--scope`, `--only` | `evidence.md`, `evidence.json` | In command trước khi chạy; timeout; không tự chạy deploy |
| `scripts/worktree.py` | adapter, branch/ticket | worktree + baseline | Không `--force`; kiểm tra path; không xoá worktree khác |
| `scripts/traceability.py` | bảng Markdown | lỗi/thiếu row | Chỉ đọc |
| `orchexa-test/scripts/gate.py` | lane, `--full` | bảng pass/fail + baseline | Wrapper của `e2e-report.sh`; không sửa script gốc |
| `orchexa-test/scripts/baseline.py` | JUnit XML | diff baseline | Dùng `check_fe_vitest_baseline.py` |
| `orchexa-ship/scripts/env_keys.py` | diff | keys add/remove | Names only; không đọc giá trị |
| `orchexa-debug/scripts/trace.py` | conversation/message id | summary | Không in raw JSON; redact secrets |
| `orchexa-debug/scripts/probe.py` | subsystem | checklist probe | Chỉ đọc/health check; không sửa state |

Thiết kế theo [Using scripts](https://agentskills.io/skill-creation/using-scripts): self-contained,
`--help`, non-interactive, output có cấu trúc, lỗi nêu cách sửa. Python 3 (kit đã yêu cầu
Python cho installer), tránh Bash-only để chạy được trên Windows/WSL.

---

## 10. Rủi ro & giảm thiểu

| Rủi ro | Mức | Giảm thiểu |
|---|---|---|
| Sửa description làm trigger regress | Cao | Trigger eval trước/sau; chỉ merge khi ≥ baseline; giữ acceptable alternatives |
| Gộp 23 skill làm mất tri thức | Cao | Move, không xoá; domain owner review; giữ stub 1 release; search index references |
| Cài kit vào Orchexa gây nhiễu 38 skill | Cao | `--profile core`; dry-run worktree; đo catalog; không cài discovery/Spec Kit |
| Planner external vs Spec Kit kéo dài | Trung bình | P0 chỉ dùng core; quyết định planner ở Phase 2; pilot 1 feature nếu chọn Spec Kit |
| `.claude`/`.agents` symlink không portable | Trung bình | Generated copies + parity check; symlink chỉ trên macOS; CI check |
| AGENTS.md trim làm mất trap | Trung bình | Giữ link; review với tech lead; pilot 1 tuần; không xoá nội dung, chỉ move |
| Full gate quá chậm | Trung bình | `test_fast`/`test_full`; fast cho task/worktree, full cho final; không nới gate |
| Script chạy lệnh nguy hiểm | Cao | Read-only mặc định; in command; `--dry-run`; không deploy/merge; review script |
| Risk area thu hẹp làm giảm rigor | Trung bình | Chuyển broad modules sang `review.human_required_for`; ghi rationale; audit lại |

---

## 11. Quyết định cần chốt

1. **Planner của Orchexa:** giữ `docs/unicorn-saas-plan` + QA-SDLC (external) hay adopt Spec Kit
   cho feature mới? Đề xuất: external trong quý này; pilot Spec Kit 1 feature nếu muốn.
2. **Nơi đặt Orchexa skill pack:** trong repo Orchexa (khuyến nghị) hay trong
   `ai-engineering-kit/adapters/orchexa/skills/`? Nếu trong kit, checker phải hỗ trợ field
   `license`/`metadata` và inventory riêng.
3. **Nguồn chuẩn skills:** `.agents/skills` (đang mới hơn) hay `.claude/skills`? Symlink hay
   generated copy?
4. **Harness chính để eval:** Claude Code, Codex, hay cả hai? Cần tối thiểu một harness chạy
   được trigger + behavior eval.
5. **Có được trim `AGENTS.md`/`CLAUDE.md` không?** Nếu không, ít nhất dedupe `CLAUDE.md` →
   `@AGENTS.md` và chuyển session log ra docs.
6. **Owner & thời gian:** ai sở hữu kit, adapter, từng hub (debug/test/ship/integrate/agent/plan)?

---

## 12. Phụ lục — bằng chứng & lệnh kiểm tra

### 12.1. Kit

```bash
cd ai-engineering-kit
UV_CACHE_DIR=/tmp/aiek-uv-cache bash scripts/check.sh
# OK: 15 skills; YAML, references, inventories and wrappers consistent

python3 - <<'PY'
# đếm body/description của kit
...
PY
```

Kết quả: 15 skill, 1.059 dòng body, 3.632 ký tự description, 13 reference files (761 dòng),
0 `skills/*/scripts`, 0 `evals/`. Body dài nhất 106 dòng (`systematic-debugging`).

### 12.2. Orchexa

```bash
cd /Users/moment/Projects/work/ORCHEXA/codebase/saas/orchexa-be
# frontmatter/case/description
python3 - <<'PY'
...
PY

# drift
diff -rq .claude/skills .agents/skills

# tham chiếu chết
git log --all --oneline -- CLAUDE-Edupia.md
git log --all --oneline -- .claude/skills/orchexa-edupia-trace-root-cause-from-profile
find . -name tom_tat.py -not -path '*/node_modules/*'

# risk areas
python3 - <<'PY'
import subprocess, fnmatch
files = subprocess.check_output(['git','ls-files'], text=True).splitlines()
for g in [...]:
    print(g, sum(fnmatch.fnmatch(f, g) for f in files))
PY

# worktree
git worktree list
```

Kết quả chính:

- 23 skill BE; 8.340 dòng body; 12.253 ký tự description.
- 5 skill không frontmatter; 7 `skill.md`; 2 description > 1.024; 5 skill > 500 dòng; max 1.475.
- 7 file khác giữa `.claude` và `.agents`.
- 450/4.285 file tracked khớp `risk_areas`.
- `AGENTS.md`/`CLAUDE.md`: 999 dòng / 50.458 byte mỗi file, diff chỉ H1.
- Không có `.specify/`/`specs/`; `qa.yml` tồn tại; `CLAUDE-Edupia.md`, skill edupia,
  `tom_tat.py` không còn.

### 12.3. Tài liệu tham chiếu

- [Agent Skills — Quickstart](https://agentskills.io/skill-creation/quickstart)
- [Agent Skills — Best practices](https://agentskills.io/skill-creation/best-practices)
- [Agent Skills — Optimizing descriptions](https://agentskills.io/skill-creation/optimizing-descriptions)
- [Agent Skills — Evaluating skills](https://agentskills.io/skill-creation/evaluating-skills)
- [Agent Skills — Using scripts](https://agentskills.io/skill-creation/using-scripts)
- [Agent Skills — Specification](https://agentskills.io/specification)
- [Audit nội bộ 2026-10-17](audit-2026-10-17.md)
- [Upstream mapping](upstream-mapping.md)
