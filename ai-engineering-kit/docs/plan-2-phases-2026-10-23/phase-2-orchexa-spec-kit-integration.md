# Phase 2 — Tích hợp Spec Kit vào Orchexa (kế hoạch, chưa triển khai)

**Trạng thái:** Kế hoạch thiết kế & triển khai — **chưa thực thi**. Không file Orchexa nào bị thay đổi bởi tài liệu này.
**Phạm vi:** `orchexa-be` (và `orchexa-fe` khi cần), áp dụng sau khi [Phase 1](phase-1-kit-optimization.md) hoàn tất.
**Nguồn:** [Đánh giá & đề xuất 2026-10-23](../skills-audit-and-plan-2026-10-23.md).
**Thời lượng dự kiến:** 4–6 tuần sau Phase 1 (pilot + rollout), 1 kỹ sư + tech lead/QA + domain owner.
**Câu hỏi trung tâm:** làm sao dùng Spec Kit (`spec.md`, `plan.md`, `tasks.md`, `research.md`,
`data-model.md`, `contracts/`, `quickstart.md`, `constitution.md`) mà **vẫn giữ cấu trúc tài liệu
hiện có của Orchexa**, đồng thời **Spec Kit có đủ dữ liệu** để plan/tasks/implement chính xác.

---

## 0. Kết luận thiết kế (TL;DR)

1. **Spec Kit là lớp thực thi theo feature** (`specs/`), không phải lớp product/portfolio.
   `docs/unicorn-saas-plan/` vẫn là nơi sở hữu PRD, roadmap, quyết định, case library.
2. **Không di chuyển, không viết lại, không xoá** cấu trúc docs hiện có. Chỉ thêm:
   `specs/` (Spec Kit), `specs/README.md`, `specs/INDEX.md`, `ROADMAP.md` (index mỏng),
   `.specify/` (Spec Kit), `.aiek/` (kit), và các index/archive marker.
3. **Một fact, một owner.** `specs/` sở hữu scope/AC/task của feature; docs sở hữu kiến thức
   bền vững; QA docs sở hữu test/UAT/evidence; Plane sở hữu trạng thái; adapter sở hữu command/risk;
   constitution sở hữu nguyên tắc kỹ thuật. Các lớp **link**, không copy.
4. **`specs/` đặt ở root repo**, không đặt trong `docs/`. Đây là ngoại lệ có chủ đích: Spec Kit
   hard-code `SPECS_DIR="$REPO_ROOT/specs"` trong `create-new-feature.sh` (bản 1.2.3.dev0);
   `SPECIFY_FEATURE_DIRECTORY` chỉ override được sau khi tạo. Đặt root `specs/` là ít ma sát nhất,
   và vẫn giữ nguyên `docs/` của Orchexa.
5. **`ROADMAP.md` chỉ là index mỏng** trỏ về `docs/unicorn-saas-plan/05-delivery/` và
   `roadmap/roadmap.json`; không nhân bản WP/wave.
6. **Legacy planners phải bị đóng băng:** `docs/superpowers/plans|specs`, `.planning/`,
   `docs/01-planning/ROADMAP.md` cũ, `docs/INDEX.md` cũ. Không tạo nội dung mới ở đó; chỉ archive
   hoặc trỏ sang nguồn mới.
7. **Spec Kit đủ dữ liệu** nhờ 4 nguồn: PRD/roadmap docs (WHAT/WHY), architecture/API docs (HOW),
   adapter + constitution (command/risk/principle), QA/DoD/case library (acceptance/verify).
   `spec.md` giữ traceability (OSA/M/W/DEC/PRD) và link; `plan.md`/`tasks.md` lấy command và test
   layer từ adapter/preset.

**Không làm:** migrate toàn bộ lịch sử vào `specs/`; viết lại tất cả PRD; xoá `docs/superpowers`
hay `.planning`; thay Plane bằng `state.json`; big-bang toàn repo.

---

## 1. Hiện trạng Orchexa (bằng chứng)

### 1.1. Các lớp tài liệu đang tồn tại

| Lớp | Đường dẫn | Vai trò hiện tại | Vấn đề |
|---|---|---|---|
| Product / portfolio | `docs/unicorn-saas-plan/` | PRD M01–M07, strategy, discovery, MVP scope, delivery W0–W4, decisions DEC, metrics, case library, MCP eval | Đang DRAFT; nhiều file; chưa có index "đâu là nguồn sự thật" |
| Product cũ | `docs/01-planning/` (21 file top-level) | ROADMAP/PRODUCT_REQUIREMENTS VoiceAgent OS 2026-01 | Đã cũ (2026-01-04) so với `unicorn-saas-plan` (2026-09/10); dễ bị đọc nhầm |
| Implementation cũ | `docs/02-implementation/` (141 file) | customer-journey, llm-reliability, orchexa-mcp | Lịch sử kỹ thuật; không phải plan hiện tại |
| Kiến trúc / API / SDK / Ops | `docs/02-architecture/`, `docs/03-guides/`, `docs/04-api/`, `docs/04-integrations/`, `docs/05-sdk/`, `docs/06-operations/`, `docs/ONBOARDING/` | Kiến thức bền vững | Tốt; cần được link từ spec/plan |
| QA / UAT / evidence | `docs-e2e/`, `docs/qa/`, `docs/uat/`, `docs/verification/`, `docs/evidence/` | QA-SDLC 7 pha/4 cổng, DoD, UAT, evidence | Tốt; cần nối vào `tasks.md`/DONE |
| Legacy planner | `docs/superpowers/plans/` (26 file), `docs/superpowers/specs/` (13 file) | Plan/spec kiểu Superpowers 2026-03..09 | Trùng vai trò Spec Kit; là planner thứ hai nếu dùng tiếp |
| Session notes | `.planning/` (27 file top-level) | Handoff, gap analysis, plan tạm | Không phải nguồn sự thật; dễ trôi |
| Work tracking | Plane `OSA-*` | Trạng thái thật của team | `docs/unicorn-saas-plan/tracker/state.json` dừng cập nhật tay từ 14/10/2026 |
| Generated views | `docs/unicorn-saas-plan/roadmap/roadmap.json`, `13-go-live/danh-gia.json`, `tracker/index.html` | Báo cáo CEO/PO | Nên giữ; chỉ link, không sửa tay |
| Agent instructions | `AGENTS.md`, `CLAUDE.md` (999 dòng / 50.458 byte mỗi file) | Workflow, trap, deploy env | Trùng lặp; quá lớn để always-on |
| Agent skills | `.claude/skills` / `.agents/skills` (23 skill) | Domain playbooks | Chất lượng đóng gói kém; drift 7 file |

### 1.2. Điểm mạnh có thể tận dụng ngay

- **PRD template đã gần Spec Kit**: `docs/unicorn-saas-plan/03-modules/README.md` có user story,
  acceptance, FR ID ổn định (`<MOD>-FR-xx`), MoSCoW, data contract, MCP tools, UI, NFR, metrics,
  open questions, MVP cut. Đây là đầu vào lý tưởng cho `spec.md`/`plan.md`.
- **Delivery plan có WP ID + wave**: `05-delivery/work-breakdown.md` (W0.1, J1, C1, …) và
  `roadmap-and-milestones.md` (W0–W4, exit criteria) → đầu vào cho `tasks.md`/`ROADMAP.md`.
- **Decision log có ID**: `07-decisions/decision-log.md` (DEC-00…DEC-22) → đầu vào cho
  `research.md`/`plan.md`/`spec.md` assumptions.
- **Quality gates + DoD rất cụ thể**: `05-delivery/quality-gates.md`, `docs-e2e/QA-SDLC-WORKFLOW.md`,
  `docs/unicorn-saas-plan/plane-pages/01-definition-of-done.md`, `02-release-checklist.md`.
- **Case library/fixture**: `09-case-library/` (RC-01…RC-06, VC-*), `coverage-matrix.md` →
  acceptance scenarios cho `spec.md` và test cases cho `tasks.md`.
- **Evidence pattern**: `docs/qa/OSA-561-review-QC.md`, `docs/evidence/OSA-561/`,
  `docs/qa/OSA-598-*` → nơi DONE report link tới.

### 1.3. Spec Kit đã có sẵn trên máy (probe)

- `specify 1.2.3.dev0` tại `~/.local/bin/specify`.
- `specify init` tạo `.specify/` gồm `memory/constitution.md`, `templates/{spec,plan,tasks,
  constitution}-template.md`, `scripts/`, `workflows/`, `integrations/`.
- `create-new-feature.sh` hard-code `SPECS_DIR="$REPO_ROOT/specs"`; feature dir `NNN-<slug>`;
  hỗ trợ `--short-name`, `--number`, `--timestamp`; `SPECIFY_FEATURE_DIRECTORY` override cho
  các command sau.
- Preset hỗ trợ `replace`, `append`, `prepend`, `wrap`; preset priority thấp hơn = ưu tiên cao hơn.
- Đã thử trong project tạm: cài `aiek-core` (priority 10) + một preset Orchexa giả (priority 5);
  command `speckit.specify` render **xếp lớp** đúng: Orchexa wrapper → kit wrapper → core.
  Template append dùng cùng cơ chế; cần xác nhận lại trong pilot (xem §5).

```bash
# Probe trong project tạm — KHÔNG chạm Orchexa
specify init . --here --integration codex --ignore-agent-tools --non-interactive --force
bash ai-engineering-kit/scripts/install.sh . --harness codex --speckit
specify preset add --dev /tmp/orchexa-preset --priority 5
# Quan sát: .agents/skills/speckit-specify/SKILL.md có cả "Orchexa Specify Rules"
# và "Feature Brief Intake (AI Engineering Kit)" trước core template.
```

---

## 2. Kiến trúc đích: 6 lớp, một owner cho mỗi fact

### 2.1. Mô hình 6 lớp

```text
┌─ 1. AGENT INSTRUCTIONS ─────────────────────────────────────────────┐
│ AGENTS.md / CLAUDE.md (map + router) · .aiek/ (workflow + adapter)  │
│ .specify/memory/constitution.md (nguyên tắc kỹ thuật)               │
├─ 2. PRODUCT / PORTFOLIO ────────────────────────────────────────────┤
│ docs/unicorn-saas-plan/  ·  ROADMAP.md (index mỏng)                 │
│ 00-strategy · 03-modules/PRD · 04-mvp-scope · 05-delivery ·          │
│ 06-metrics · 07-decisions · 09-case-library · 10-mcp-evaluation      │
├─ 3. DURABLE ENGINEERING ────────────────────────────────────────────┤
│ docs/02-architecture · docs/03-guides · docs/04-api ·               │
│ docs/04-integrations · docs/05-sdk · docs/06-operations · ONBOARDING│
├─ 4. FEATURE EXECUTION (SPEC KIT) ───────────────────────────────────┤
│ specs/<NNN>-<OSA>-<slug>/                                           │
│ spec.md · plan.md · tasks.md · research.md · data-model.md ·        │
│ contracts/ · quickstart.md                                          │
├─ 5. QUALITY / EVIDENCE ─────────────────────────────────────────────┤
│ docs-e2e/ (QA-SDLC, DoD, UAT, coverage) · docs/qa · docs/uat ·      │
│ docs/verification · docs/evidence                                   │
└─ 6. WORK TRACKING ──────────────────────────────────────────────────┘
  Plane OSA-* (status source) · roadmap/roadmap.json · 13-go-live
```

**Quy tắc:** lớp trên **không** viết lại nội dung lớp dưới; chỉ đọc và link. Lớp 4 là nơi duy nhất
tạo plan/tasks cho feature.

### 2.2. Authority matrix

| Fact / artifact | Owner duy nhất | File | Ai đọc |
|---|---|---|---|
| Vision, ICP, P1–P11 | Product | `docs/unicorn-saas-plan/00-strategy/` | spec/plan/constitution |
| Module requirements, FR ID, MoSCoW | Product | `docs/unicorn-saas-plan/03-modules/MXX/PRD.md` | spec (giữ ID) |
| MVP scope, out-of-scope | Product | `04-mvp-scope/` | spec/ROADMAP |
| Roadmap W0–W4, WP ID | Delivery | `05-delivery/roadmap-and-milestones.md`, `work-breakdown.md` | ROADMAP/tasks |
| Quality gates, DoD, release | QA/Lead | `05-delivery/quality-gates.md`, `docs-e2e/` | tasks/verify/accept |
| Decisions DEC-xx | PO/Founder | `07-decisions/decision-log.md` | spec/plan/research |
| Architecture, MCP-first, 3-layer | Tech lead | `docs/02-architecture/`, `docs/unicorn-saas-plan/02-architecture/` | plan/research |
| API, contracts, events | Tech lead | `docs/04-api/`, `docs/04-integrations/` | plan/contracts |
| Feature scope/AC/tasks | Feature owner | `specs/<feature>/` | implement/verify/review |
| Test cases/fixtures | QA | `docs-e2e/TEST-COVERAGE-PLAN.md`, `09-case-library/` | spec/tasks/accept |
| Evidence, QC, UAT | QA/Owner | `docs/qa/`, `docs/evidence/`, `docs/verification/`, `docs/uat/` | DONE/accept |
| Work status | Team | Plane `OSA-*` | humans; specs link ID |
| Commands, risk, baseline | Tech lead | `.aiek/adapter.md` | execute/verify |
| Engineering principles | Tech lead | `.specify/memory/constitution.md` | plan/constitution check |
| Agent routing | Team | `AGENTS.md`/`CLAUDE.md` | agent |

### 2.3. Cây thư mục đích

```text
orchexa-be/
├─ AGENTS.md / CLAUDE.md          # map + router; CLAUDE.md = @AGENTS.md
├─ ROADMAP.md                     # index mỏng → docs/unicorn-saas-plan/05-delivery
├─ .specify/
│  ├─ memory/constitution.md      # P1–P11, DoD, quality gates, LLM chokepoints
│  ├─ templates/                  # Spec Kit; preset Orchexa bổ sung
│  └─ scripts/                    # Spec Kit scripts
├─ .aiek/
│  ├─ adapter.md                  # command/risk/baseline/planning mode
│  ├─ core/                       # kit policies
│  └─ adapter/references/         # trap/test layers/release (optional)
├─ specs/
│  ├─ README.md                   # authority + naming + flow
│  ├─ INDEX.md                    # NNN ↔ OSA ↔ M/W ↔ PRD ↔ status
│  └─ 001-OSA-561-.../
│     ├─ spec.md
│     ├─ plan.md
│     ├─ tasks.md
│     ├─ research.md
│     ├─ data-model.md
│     ├─ contracts/
│     └─ quickstart.md
├─ docs/                          # GIỮ NGUYÊN cấu trúc hiện có
│  ├─ README.md                   # docs map + trạng thái active/legacy
│  ├─ unicorn-saas-plan/          # product/portfolio
│  ├─ 02-architecture/ ...        # durable engineering
│  ├─ 01-planning/                # legacy (mark)
│  ├─ 02-implementation/          # historical (mark)
│  └─ superpowers/                # archive (mark)
├─ docs-e2e/                      # QA-SDLC, DoD, UAT, coverage
├─ docs/qa, docs/uat, docs/verification, docs/evidence  # records
├─ .planning/                     # session scratch; archive marker
└─ migrations/, bridge/, scripts/, ...  # code
```

### 2.4. Vì sao `specs/` ở root, không nằm trong `docs/`

- Spec Kit 1.2.3.dev0: `create-new-feature.sh` dòng `SPECS_DIR="$REPO_ROOT/specs"`; feature dir
  `specs/NNN-...`. `SPECIFY_FEATURE_DIRECTORY` chỉ override **sau** khi đã có feature dir.
- Đặt `docs/specs/` sẽ phải tạo thủ công/symlink hoặc set env cho mọi command → tăng ma sát,
  dễ sai khi chạy nhiều agent.
- Root `specs/` là chuẩn của Spec Kit, dễ nhận diện; `docs/` của Orchexa không bị xáo trộn.
- Ghi rõ trong `specs/README.md`: "Đây là lớp execution; product/engineering docs nằm ở `docs/`."
- Nếu lãnh đạo bắt buộc mọi thứ dưới `docs/`, dùng `SPECIFY_FEATURE_DIRECTORY=docs/specs/<...>`
  + symlink `specs -> docs/specs`; **không khuyến nghị** vì thêm một nguồn lỗi.

| Phương án | Ưu | Nhược | Kết luận |
|---|---|---|---|
| Root `specs/` | Đúng chuẩn Spec Kit; không cấu hình; `docs/` nguyên vẹn; agent dễ tìm | Thêm một folder ngoài `docs/` | **Khuyến nghị** |
| `docs/specs/` + env/symlink | Mọi tài liệu dưới `docs/` | `create-new-feature` vẫn tạo root `specs/`; mọi command cần env; dễ quên | Không khuyến nghị |
| Native docs, không Spec Kit | Không thêm folder | Mất flow specify/plan/tasks; phải tự viết script/check; không có `tasks.md` chuẩn | Chỉ khi quyết định không dùng Spec Kit |

### 2.5. Naming, index, ROADMAP

- Feature dir: `NNN-OSA-<id>-<slug>` (ví dụ `001-OSA-561-export-csv`) hoặc `NNN-<slug>` nếu
  chưa có ticket. `NNN` 3 chữ số, tăng dần; dùng `--short-name`/`--number`.
- Spec Kit có thể chuẩn hoá short-name thành lowercase/hyphen (`001-osa-561-...`); chấp nhận
  miễn `spec.md` giữ OSA trong Traceability. Nếu cần chữ hoa, rename thư mục ngay sau khi tạo
  và trước khi chạy `specify`.
- `spec.md` có bảng **Traceability**: OSA, M/W, PRD link, DEC, WP, branch, PR.
- `specs/INDEX.md` sinh bằng `scripts/spec_index.py`:
  `| NNN | slug | OSA | M/W | PRD | status | branch | PR |`
- `ROADMAP.md`: chỉ có wave W0–W4 + link `05-delivery/roadmap-and-milestones.md`,
  `roadmap/roadmap.json`, `04-mvp-scope`; **không** chép WP.
- `specs/README.md`: authority, naming, flow, "không tạo plan thứ hai".

---

## 3. Spec Kit ↔ Orchexa docs: mapping & dữ liệu đủ

### 3.1. Bảng mapping

| Orchexa doc | Dùng vào Spec Kit | Cách dùng |
|---|---|---|
| `00-strategy/vision-and-north-star.md`, `product-principles.md` | `constitution.md`, `spec.md` context | Trích nguyên tắc; link |
| `01-discovery/current-state-audit.md`, `jobs-to-be-done.md` | `spec.md` Problem/Users/JTBD | Link; không copy toàn bộ |
| `02-architecture/three-layer-model.md`, `core-concepts-and-contracts.md`, `extension-points.md`, `mcp-first-design.md` | `plan.md` Architecture/Technical Context; `research.md` | Link + tóm tắt quyết định |
| `03-modules/MXX/PRD.md` | `spec.md` User Stories/FR/Acceptance/Scope; `plan.md` Data/MCP/UI/NFR | Giữ ID `US-x`, `<MOD>-FR-xx`; spec là **slice**, không chép PRD |
| `04-mvp-scope/README.md`, `scope-options.md`, `out-of-scope.md` | `spec.md` Scope/Success; `ROADMAP.md` | Link; MVP boundary |
| `05-delivery/roadmap-and-milestones.md` | `ROADMAP.md`; `spec.md` context | Index; không copy |
| `05-delivery/work-breakdown.md` (WP ID) | `tasks.md` Task ID/Phase | Map WP → task; giữ WP ID trong traceability |
| `05-delivery/quality-gates.md` | `tasks.md` Verify; `plan.md` QA Gates | Copy **điều kiện**, link nguồn |
| `05-delivery/rollout-and-migration.md` | `plan.md` Rollout/Rollback | Link + quyết định cụ thể |
| `06-metrics/metrics-framework.md` | `spec.md` Success Criteria | Link; chọn metric đo được |
| `07-decisions/decision-log.md` (DEC) | `spec.md` Assumptions; `plan.md` Decisions; `research.md` | Giữ DEC ID; không tự đổi quyết định |
| `08-appendix/glossary.md` | `spec.md`/`plan.md` glossary | Link |
| `09-case-library/RC-*.md`, `coverage-matrix.md` | `spec.md` Acceptance Scenarios; `tasks.md` test cases | Map RC/VC → scenario/fixture |
| `10-mcp-evaluation/` | `research.md`; `spec.md` success | Link rubric/ngưỡng |
| `docs-e2e/QA-SDLC-WORKFLOW.md` | `constitution.md`, `tasks.md` Verify, `accepting-change` | Map 4 cổng; link |
| `docs-e2e/TEST-COVERAGE-PLAN.md` | `tasks.md` test layer/coverage | Link module gap |
| `docs-e2e/QA-SIGNOFF-PLAYBOOK.md`, `MANUAL-UAT-EXECUTION.md` | `spec.md` person-checkable AC; `accepting-change` | Link |
| `docs/qa/OSA-*`, `docs/evidence/OSA-*`, `docs/verification/` | DONE report; PR; `accepting-change` | Link evidence, không copy |
| `docs/02-architecture/`, `docs/03-guides/`, `docs/04-api/`, `docs/04-integrations/`, `docs/05-sdk/`, `docs/06-operations/`, `docs/ONBOARDING/` | `plan.md` Constraints/Contracts/Quickstart | Link đúng mục |
| `docs/01-planning/` (ROADMAP cũ, PRODUCT_REQUIREMENTS cũ) | Legacy/historical: không dùng làm nguồn cho feature mới; file còn active phải được owner xác nhận và chuyển sang docs hiện hành | Mark legacy; chỉ đọc lịch sử |
| `docs/superpowers/plans\|specs`, `.planning/` | Không dùng làm plan | Archive/input; migrate chỉ feature còn active |
| Plane `OSA-*` | `spec.md` Traceability; `specs/INDEX.md` | Link ID; status do Plane |
| `tracker/state.json`, `roadmap/roadmap.json` | `ROADMAP.md`/index | Generated/legacy; không sửa tay |

### 3.2. `spec.md` — đủ dữ liệu để plan/tasks

`spec.md` tối thiểu gồm:

- **Header**: feature name, OSA, M/W, PRD link, DEC liên quan, status, owner, branch.
- **Problem / Users / JTBD**: 2–4 đoạn, link `01-discovery`.
- **User Stories**: P1/P2/P3; mỗi story có "Independent Test" và acceptance scenarios
  Given/When/Then; giữ `US-x` của PRD nếu có.
- **Functional Requirements**: bảng `FR-001` + cột `PRD ref` (`JRN-FR-01`) + MoSCoW + test layer.
  Không bịa FR mới nếu PRD đã có; nếu cần, ghi rõ "new, PRD gap".
- **Scope / Out of scope / Non-goals**: link `04-mvp-scope` và PRD "MVP cut".
- **Orchexa Constraints**: P1 (no tenant taxonomy), P6 (outbound gate), P7 (import no trigger),
  P8 (version), LLM chokepoints, multi-tenant, security, no secrets.
- **Success Criteria**: metric đo được từ `06-metrics`; không chỉ "nhanh/ổn định".
- **Dependencies**: module, service, provider, migration, FE repo, external system.
- **Assumptions / Open questions**: DEC đã chốt vs cần `clarify`/NEEDS DECISION.
- **Traceability**: bảng OSA/M/W/WP/DEC/PRD/docs.
- **Docs to update**: list docs sẽ cập nhật trong cùng feature.

### 3.3. `plan.md` — đủ dữ liệu để implement

- Summary + Technical Context (Python 3.12/FastAPI/Next.js/Postgres/Qdrant/Redis/Langfuse).
- Constitution Check: P1/P3/P4/P6/P7/P8/P10 + TDD + docs authority.
- Architecture boundaries: `bridge/app/**` vs `tenants/`, services, outbound gate, LLM gateway.
- Data/Migrations: bảng, migration `NNN_*.sql`, số range, backfill/reversible.
- Contracts: API/event/MCP tool; link `docs/04-api`, `docs/04-integrations`.
- LLM/Provider: model allowlist, `gw.call()`, `reply_finalizer`, cost/fallback.
- Test Strategy: pure/integration/e2e/agent-eval; file paths; exact commands; baseline.
- QA Gates: Gate 0/1/1b/2; `scripts/e2e-report.sh`, `scripts/uat-scenarios.sh`.
- Rollout/Rollback: feature flag, env keys, staging check, rollback rehearsal.
- Docs to update + release note + `## Production .env setup`.
- Complexity tracking: deviation from constitution with reason.

### 3.4. `tasks.md` — đủ dữ liệu để thực thi

- Format `[ID] [P?] [Story] Description`, path chính xác.
- Phase: Setup → Foundational → từng US → Polish/Release.
- Mỗi task có **`Verify:`** = command hoặc manual check cụ thể; test layer.
- Task test-first cho behavior; SQL mới có integration test Postgres thật.
- Migration task ghi số range; env task ghi tên key (không value); docs task ghi file.
- Release task: cập nhật `specs/INDEX.md`, `ROADMAP.md` (nếu cần), docs, release note.
- `tasks.md` không phải Plan B: không thay `spec.md`/`plan.md`; nếu plan sai, sửa artifact.

### 3.5. Các artifact khác

| Artifact | Nội dung | Nguồn |
|---|---|---|
| `research.md` | câu hỏi mở, benchmark, DEC, lựa chọn provider/model, trade-off | DEC log, `10-mcp-evaluation`, plan |
| `data-model.md` | schema/migration mapping, index, backfill | PRD data contract, `migrations/` |
| `contracts/` | OpenAPI/JSON schema/event/MCP tool | `docs/04-api`, `docs/04-integrations` |
| `quickstart.md` | cách chạy/verify local, seed, feature flag | `docs/03-guides`, adapter commands |
| `constitution.md` | P1–P11, DoD, quality gates, LLM chokepoints, docs authority | `00-strategy`, `05-delivery/quality-gates`, `AGENTS.md` |

### 3.6. Quy tắc chống trùng lặp

1. **Một fact, một owner** (authority matrix §2.2). Lớp khác chỉ link + tóm tắt 1–3 dòng.
2. **Spec là slice, không phải bản sao PRD.** Giữ ID; link PRD.
3. **`ROADMAP.md` mỏng**, không chép wave/WP; nguồn là `05-delivery`.
4. **Không tạo plan mới** trong `.planning/`, `docs/superpowers/`, hay `docs/01-planning/`.
5. **Plane là status**; spec/tasks chỉ link OSA, không duplicate status board.
6. **Mọi task có Verify**, mọi PR có spec link, mọi DONE có evidence link.
7. **Cập nhật nơi sở hữu**, không cập nhật bản copy. Nếu spec và PRD lệch: PRD/spec owner quyết;
   ghi DEC nếu đổi scope.

---

## 4. Preset & template cho Orchexa

### 4.1. Cơ chế

- `adapters/orchexa/speckit-preset/` → cài `--priority 5` (cao hơn `aiek-core` priority 10).
- `provides.templates`:
  - `spec-template` — `append`
  - `plan-template` — `append`
  - `tasks-template` — `append`
  - `constitution-template` — `replace` (hoặc seed `constitution.md`)
  - `speckit.specify` / `speckit.plan` / `speckit.tasks` — `wrap` nếu cần thêm rule (đã xác nhận
    command wrap xếp lớp được với `aiek-core`; template append dùng cùng resolver, test lại pilot).
- Không sửa core Spec Kit; không fork command; chỉ append/wrap.

### 4.2. Nội dung preset

**`spec-template` append**
- `## Orchexa Traceability`: OSA, M/W, WP, DEC, PRD link, branch/PR.
- `## Orchexa Constraints`: P1, P6, P7, P8, LLM chokepoints, multi-tenant, no secrets.
- `## Test Layers`: pure/integration/e2e/agent-eval + command.
- `## Docs to update`: list.
- `## Scope / Non-goals`: link MVP scope.

**`plan-template` append**
- `## Orchexa Architecture & Boundaries`
- `## Data & Migrations` (flat `NNN_*.sql`, range, backfill)
- `## Contracts & MCP Tools`
- `## LLM / Chokepoints`
- `## Test Strategy` (4 layers + exact commands)
- `## QA Gates` (Gate 0/1/1b/2)
- `## Rollout / Rollback / Env`
- `## Docs to update`

**`tasks-template` append**
- `Verify:` bắt buộc; test layer; migration range; docs update; release note/env.
- `[P]` strict (theo kit).
- Task test-first; SQL integration test.

**`constitution-template` / constitution**
- P1–P11 (từ `00-strategy/product-principles.md`).
- TDD + behavioral test + gate `e2e-report.sh`.
- LLM chokepoints (`llm_gateway`, `reply_finalizer`, model allowlist).
- Migrations theo tên file; env key names only.
- Docs authority + "no second planner".
- QA gates/DoD.
- Governance: amend cần DEC + review.

### 4.3. `preset.yml` mẫu

```yaml
schema_version: "1.0"
preset:
  id: "orchexa-project"
  name: "Orchexa project rules"
  version: "0.1.0"
  description: "Orchexa-specific Spec Kit additions layered on aiek-core."
requires:
  speckit_version: ">=1.0.0"
provides:
  templates:
    - type: "template"
      name: "spec-template"
      file: "templates/spec-template.md"
      strategy: "append"
    - type: "template"
      name: "plan-template"
      file: "templates/plan-template.md"
      strategy: "append"
    - type: "template"
      name: "tasks-template"
      file: "templates/tasks-template.md"
      strategy: "append"
    - type: "template"
      name: "constitution-template"
      file: "templates/constitution-template.md"
      strategy: "replace"
    - type: "command"
      name: "speckit.specify"
      file: "commands/speckit.specify.md"
      strategy: "wrap"
```

---

## 5. Workflow end-to-end

```text
Plane OSA / PRD slice
        │
        ▼
intaking-ticket (nếu có AC) ─► AC checkable? ─no─► BLOCKED (questions)
        │ yes
        ▼
classification (SMALL / NORMAL / LARGE / INFRA)
        │
        ├─ SMALL ──► executing-task → verifying-change → reviewing-change → DONE
        │
        ├─ NORMAL/LARGE
        │    ├─ unclear how? → shaping-feature → Feature Brief
        │    ├─ specify (với brief + PRD link + OSA) → spec.md
        │    ├─ clarify (DEC/NEEDS CLARIFICATION)
        │    ├─ plan → plan.md/research.md/data-model.md/contracts/
        │    ├─ tasks → tasks.md (Verify từng task)
        │    ├─ ready gate → READY TO BUILD
        │    ├─ worktree (LARGE) → execute → verify → review
        │    └─ authoring-pr → accepting-change → DONE
        │
        └─ INFRA → shipping-infrastructure → accepting-change (ops)
```

**Lane & spec:**

| Lane | Spec? | Artifact |
|---|---|---|
| SMALL | Không | request + adapter; DONE ngắn |
| NORMAL | Có | `specs/<feature>/spec.md`, `plan.md`, `tasks.md` |
| LARGE | Có + worktree | như trên + `research.md`/`data-model.md`/`contracts/`; independent review |
| INFRA | Không bắt buộc | decision record + ops evidence; dùng `shipping-infrastructure` |

**Chống ceremony:**
- Small/typo/known bug → không tạo spec; dùng `executing-task`.
- Nhiều ticket nhỏ cùng một user outcome → gộp vào **một** feature spec; `specs/INDEX.md` map
  nhiều OSA vào một spec.
- Không tạo spec cho việc chỉ đổi docs/copy; dùng lane Small.
- Mỗi spec chỉ một user outcome; không nhồi 10 module vào một spec.

**Spec Kit commands** (tên render theo integration):
`/speckit-specify` (hoặc `$speckit-specify`) → `/speckit-clarify` → `/speckit-plan` →
`/speckit-tasks` → `/speckit-analyze` (optional) → `/speckit-implement`.
Kit hooks: `aiek.ready`, `aiek.verify`, `aiek.review`.

**Cập nhật sau khi xong:**
- `specs/INDEX.md` status/PR.
- `ROADMAP.md` nếu scope/wave đổi.
- Plane status (người).
- Docs nếu fact bền vững đổi (architecture/API/ops).
- Evidence vào `docs/qa`/`docs/evidence`.

---

## 6. Dọn & đóng băng tài liệu (không phá cấu trúc)

### 6.1. Chính sách

- **Không xoá** tài liệu lịch sử; chỉ **đánh dấu** active/legacy/archive và cập nhật index.
- **Không di chuyển** cây lớn (`docs/02-implementation` 141 file, `docs/superpowers` 39 file)
  trong Phase 2; chỉ thêm README/redirect.
- **Active** = `docs/unicorn-saas-plan/`, `docs/02-architecture/`, `docs/03-guides/`,
  `docs/04-api/`, `docs/04-integrations/`, `docs/05-sdk/`, `docs/06-operations/`,
  `docs/ONBOARDING/`, `docs-e2e/`.
- **Legacy/historical** = phần lớn `docs/01-planning/` (ROADMAP cũ 2026-01-04),
  `docs/INDEX.md` (2026-01-01), `docs/02-implementation/` (lịch sử), `docs/superpowers/`,
  `.planning/`. File nào còn active phải được owner xác nhận và chuyển sang docs hiện hành.

### 6.2. Việc cần làm

| Việc | File | Kết quả |
|---|---|---|
| Tạo docs map | `docs/README.md` | Bảng folder → vai trò → trạng thái → đọc khi nào |
| Cập nhật/đánh dấu index cũ | `docs/INDEX.md` | Ghi "legacy — xem docs/README.md" hoặc thay bằng map mới |
| Mark legacy | `docs/01-planning/README.md`, `docs/02-implementation/README.md`, `docs/superpowers/README.md`, `.planning/README.md` | "Legacy/archive; không phải nguồn sự thật; xem docs/README.md" |
| Product index | `docs/unicorn-saas-plan/README.md` | Đã có; thêm "read this first" + link specs/ROADMAP |
| Specs index | `specs/README.md`, `specs/INDEX.md` | Authority + naming + flow + mapping |
| Roadmap index | `ROADMAP.md` | Mỏng; link `05-delivery` + `roadmap.json` + `04-mvp-scope` |
| QA map | `docs-e2e/README.md` | Trỏ QA-SDLC, DoD, UAT, coverage |
| Tracker status | `docs/unicorn-saas-plan/tracker/README.md` | "State.json dừng cập nhật 14/10/2026; Plane là nguồn" |

### 6.3. Không làm

- Không migrate 26 Superpowers plans + 13 specs vào `specs/` hàng loạt.
- Không viết lại `docs/02-implementation` 141 file.
- Không xoá `docs/superpowers`/`.planning`.
- Không đổi Plane.
- Không tạo `docs/specs` thứ hai.

---

## 7. Dọn skills & adapter Orchexa (một phần của Phase 2)

Tóm tắt từ [audit §5](../skills-audit-and-plan-2026-10-23.md); Phase 2 thực hiện:

- 23 skill → **6 hub** + optional voice (xem audit §5.4).
- 5 skill thiếu frontmatter; 7 `skill.md`; 2 description > 1.024; name/dir FE.
- `.claude/skills` vs `.agents/skills` drift 7 file → chọn một nguồn + parity check.
- Adapter < 150 dòng; bỏ tham chiếu chết (`CLAUDE-Edupia.md`, skill edupia, `tom_tat.py`);
  sửa `qa.yml`; `worktree_dir`/`branch_pattern`; thu hẹp `risk_areas`; thêm lệnh FE;
  `test_fast`/`test_full`; baseline FE.
- `AGENTS.md`/`CLAUDE.md`: `CLAUDE.md` → `@AGENTS.md`; tách session log/env/RAG history ra docs;
  giữ `AGENTS.md` 5–10 KB.
- FE `CLAUDE.md` "Skill routing" 12 skill không tồn tại → sửa/xoá.
- Cài kit `--profile core` + `intaking-ticket`; không cài discovery/Spec Kit cũ; router block.
- Mọi skill project có owner/last_verified/metadata; reference/script/evals.

Chi tiết task nằm ở workstream P2.4.

---

## 8. Workstreams & tasks

> T-ID trong Phase 2 độc lập với T-ID của Phase 1; mỗi phase có bảng task riêng.

### P2.0 — Quyết định & chuẩn bị (2–3 ngày)

| ID | Task | Artifact | Acceptance |
|---|---|---|---|
| T01 | Chốt planner: Spec Kit cho Normal/Large; docs/unicorn-saas-plan là product layer | DEC/plan | Tech lead + PO ký |
| T02 | Chốt root `specs/`; feature naming; `ROADMAP.md` mỏng | `specs/README.md` | Được review |
| T03 | Chốt canonical skills dir (`.agents`/`.claude`), harness eval | decision | Ghi trong plan |
| T04 | Chốt docs authority + archive policy | `docs/README.md` | PO/Tech lead review |
| T05 | Chốt AGENTS/CLAUDE trim | decision | Tech lead |
| T06 | Chọn pilot feature | ticket/PRD | Có owner, scope nhỏ |

### P2.1 — Docs authority & đóng băng legacy (3–5 ngày)

| ID | Task | File | Acceptance |
|---|---|---|---|
| T07 | `docs/README.md` map active/legacy | `docs/README.md` | Mọi folder có trạng thái |
| T08 | Mark legacy | `docs/01-planning/README.md`, `docs/02-implementation/README.md`, `docs/superpowers/README.md`, `.planning/README.md` | Không còn nguồn gây nhầm |
| T09 | `docs/INDEX.md` → legacy/redirect | `docs/INDEX.md` | Trỏ docs/README |
| T10 | `specs/README.md`, `specs/INDEX.md` | `specs/` | Authority + index |
| T11 | `ROADMAP.md` mỏng | root | Link đúng; không copy WP |
| T12 | `tracker` note | `docs/unicorn-saas-plan/tracker/README.md` | Plane là nguồn |
| T13 | Link cleanup AGENTS/CLAUDE/QA docs | `AGENTS.md`, `CLAUDE.md`, `docs-e2e/README.md` | Không link chết |

### P2.2 — Cài Spec Kit + kit + adapter (2–3 ngày)

| ID | Task | Artifact | Acceptance |
|---|---|---|---|
| T14 | Worktree pilot + `specify init` | `.specify/` | `specify` chạy; templates/scripts có |
| T15 | Cài kit `--speckit --adapter orchexa --profile core` | `.aiek/`, skills | Không xung đột; catalog đo được |
| T16 | Viết `.specify/memory/constitution.md` | constitution | P1–P11/DoD/LLM/migration/docs |
| T17 | Viết adapter Orchexa <150 dòng | `.aiek/adapter.md` | Command/risk/baseline/planning; không link chết |
| T18 | Cài preset Orchexa priority 5 | `.specify/presets/` | Preset list đúng; resolve template |
| T19 | `AGENTS.md`/`CLAUDE.md` dedupe + router | root | `CLAUDE.md` = `@AGENTS.md`; ≤ 10 KB |

### P2.3 — Preset & template (3–5 ngày)

| ID | Task | File | Acceptance |
|---|---|---|---|
| T20 | spec/plan/tasks append | `adapters/orchexa/speckit-preset/templates/` | Render đúng sections |
| T21 | constitution template/replace | `.../constitution-template.md` | `speckit.constitution` điền được |
| T22 | specify/plan/tasks wrap (nếu cần) | `.../commands/` | Xếp lớp với aiek-core; render đúng |
| T23 | `specs/README.md`, `INDEX.md`, `ROADMAP.md` | `specs/`, root | Được dùng bởi pilot |
| T24 | `scripts/spec_index.py` | `scripts/` | Sinh INDEX; check drift |
| T25 | Test composition | rendered command + `setup-plan`/`create-new-feature` | Command xếp lớp; template append xuất hiện; không còn placeholder |

### P2.4 — Skills/adapter Orchexa (5–10 ngày)

| ID | Task | Acceptance |
|---|---|---|
| T26 | Fix frontmatter/case/desc/name | 0 missing, 0 lowercase, 0 desc > 1.024 |
| T27 | Chọn canonical dir + sync | `.claude`/`.agents` identical hoặc sync check |
| T28 | 6 hub + references | Mỗi hub < 200 dòng; refs < 300 |
| T29 | Scripts hub | `trace.py`, `gate.py`, `baseline.py`, `env_keys.py`… có `--help` |
| T30 | Evals hub | Mỗi hub 1 bộ trigger/task |
| T31 | Adapter fixes | < 150 dòng; risk areas; FE commands; stale refs |
| T32 | AGENTS/CLAUDE trim | ≤ 10 KB; docs link |
| T33 | FE CLAUDE routing | Không còn 12 skill ảo |
| T34 | Cài core profile | 11 skill (hoặc 12 + intaking) |

### P2.5 — Pilot (1–2 tuần)

| ID | Task | Acceptance |
|---|---|---|
| T35 | Chọn 1 feature nhỏ (không migration/billing/voice) | Có PRD/OSA; 1–2 user story |
| T36 | Feature Brief + specify | `spec.md` đủ traceability/AC |
| T37 | clarify + plan + tasks | `plan.md` đủ data/test/gates; `tasks.md` Verify |
| T38 | ready gate + implement 1 task | Test-first; verify evidence |
| T39 | verify/review/PR/accept | DONE + QA gate + evidence |
| T40 | Đo & retro | Số liệu + Go/No-Go |

### P2.6 — Rollout (1–2 tuần)

| ID | Task | Acceptance |
|---|---|---|
| T41 | 2–3 feature tiếp theo | Cùng flow; không lỗi |
| T42 | Training/guide | Team biết docs authority + spec flow |
| T43 | CI skill check + spec index check | Chạy trên PR |
| T44 | Review định kỳ | Quarterly; owner |

---

## 9. Pilot plan

**Tiêu chí chọn feature:**
- Có PRD/OSA rõ; 1–2 user story; không chạm billing/migration/voice/Meta OAuth.
- Có test layer rõ (pure/integration); không phụ thuộc provider thật.
- Owner sẵn sàng; thời gian 1–2 tuần.

**Các bước:**
1. Tạo worktree `orchexa-be-wt-spec-pilot` (+ FE nếu cần); cài `.specify`, kit, preset, adapter.
2. Viết constitution; tạo `specs/001-OSA-.../` bằng `specify`; seed từ PRD slice.
3. Chạy `clarify` nếu có DEC mở; `plan`; `tasks`; `ready`.
4. Implement 1–2 task test-first; `verify`; `review`; `authoring-pr`; `accepting-change`.
5. Ghi evidence vào `docs/qa`/`docs/evidence`; cập nhật `specs/INDEX.md`.
6. Đo: thời gian đến READY, số task phải sửa, evidence coverage, QA gate, rework, token,
   feedback của dev/QA.

**Go/No-Go:**
- Spec/plan/tasks không trùng lặp docs; dev đọc hiểu không cần hỏi lại.
- Verify/review/accept có evidence; QA gate xanh.
- Không tăng ceremony quá mức (thời gian READY ≤ 1 ngày cho feature nhỏ).
- Team thấy dễ hơn hoặc ít nhất không khó hơn; nếu không, điều chỉnh template/preset.

---

## 10. Rollout & bảo trì

- Pilot pass → chọn 2–3 feature tiếp theo (1 Normal, 1 bug/Large, 1 FE/Infra).
- Không big-bang; mỗi feature mới dùng `specs/`; feature cũ giữ nguyên.
- CI: `scripts/check_skills.py`, `scripts/spec_index.py --check`, trigger eval rút gọn.
- Version pin: Spec Kit + kit + preset; ghi trong `docs/README`/README.
- Quarterly review: skills, adapter, docs authority, eval, stale links.
- Owner: tech lead (Spec Kit/docs), QA lead (QA gates), PO (PRD/roadmap), kit maintainer (kit).

---

## 11. Acceptance (Phase 2)

- [ ] `docs/README.md` + `specs/README.md` + `specs/INDEX.md` + `ROADMAP.md` tồn tại và đúng.
- [ ] Legacy docs có marker; không có nguồn sự thật thứ hai.
- [ ] `specify` + kit + preset cài được; `preset list` đúng priority; rendered skill/template thấy lớp Orchexa + aiek-core.
- [ ] Constitution được ratify; adapter < 150 dòng; template append render đúng.
- [ ] Pilot: spec/plan/tasks đủ; implement/verify/review/accept; QA gate; evidence; DONE.
- [ ] 6 hub; 0 frontmatter thiếu; 0 `skill.md`; 0 desc > 1.024; `.claude`/`.agents` parity.
- [ ] `AGENTS.md` ≤ 10 KB; `CLAUDE.md` = `@AGENTS.md`; FE routing sạch.
- [ ] Không tạo plan mới trong `.planning`/`docs/superpowers`.
- [ ] Team sign-off + Go/No-Go.

---

## 12. Rủi ro & giảm thiểu

| Rủi ro | Mức | Giảm thiểu |
|---|---|---|
| Nhiều planner (Superpowers/.planning/Plane/docs) | Cao | Authority matrix; archive marker; chỉ `specs/` cho feature mới |
| Spec trùng PRD | Cao | Spec là slice; giữ ID; link; preset rule |
| Root `specs/` xung đột cấu trúc docs | Trung bình | Ghi rõ exception; `specs/README`; không đặt trong docs |
| Spec Kit templates không khớp Orchexa | Trung bình | Preset append/wrap; pilot; test composition |
| Context quá tải (AGENTS 50KB + 34–38 skill) | Cao | Trim AGENTS; core profile; 6 hub; one canonical skills dir |
| TDD/full gate/risk areas gây ceremony | Cao | `test_fast`/`test_full`; narrow risk; lane Small |
| `.claude`/`.agents` drift | Trung bình | One source + parity check; CI |
| Plane vs spec status | Trung bình | Plane là status; spec chỉ link |
| Spec Kit version/preset drift | Trung bình | Pin version; CI install; preset priority |
| Team không dùng | Cao | Pilot; training; template; đo; điều chỉnh |
| Secrets trong spec/evidence | Cao | Không ghi secret; dùng key name; review |

---

## 13. Out of scope

- Migrate toàn bộ 26 plan + 13 spec cũ vào `specs/`.
- Viết lại 141 file `docs/02-implementation`.
- Xoá `docs/superpowers`, `.planning`, `docs/01-planning`.
- Thay Plane hoặc đổi workflow team ngay.
- Big-bang toàn repo/team.
- Chuyển toàn bộ PRD thành spec trong một đợt.

---

## 14. Phụ lục

### A. Mẫu `spec.md`

```markdown
# Feature Specification: Xuất CSV danh sách khách

**Feature Branch**: `001-OSA-561-export-csv`
**Created**: 2026-10-23
**Status**: Draft
**Input**: OSA-561 · M04 · W2 · PRD `docs/unicorn-saas-plan/03-modules/M04-customer-360/PRD.md`

## Traceability

| Field | Value |
|---|---|
| OSA | OSA-561 |
| Module / Wave | M04 / W2 |
| WP | P1 (Customer 360) |
| PRD | M04 §5 (user story), C360-FR-xx |
| DEC | DEC-06, DEC-19 |
| Docs | 09-case-library/RC-04, docs-e2e/TEST-COVERAGE-PLAN.md |

## Problem / Users / JTBD
...

## User Stories
### US-1 — Xuất CSV theo bộ lọc (P1)
...
**Independent Test**: ...
**Acceptance Scenarios**:
1. Given ..., When ..., Then ...

## Functional Requirements
| ID | Requirement | PRD ref | MoSCoW | Test layer |
|---|---|---|---|---|
| FR-001 | ... | C360-FR-15 | M | integration |

## Orchexa Constraints
- P1 no tenant taxonomy in core; P6 outbound gate; P7 import no trigger.
- LLM calls only via `gw.call()`; customer answers via `finalize()`.
- New SQL needs real-Postgres integration test.

## Success Criteria
- SC-001: ...

## Scope / Non-goals
...

## Dependencies
...

## Assumptions / Open Questions
...

## Docs to update
- `docs/04-api/...`; `docs/02-architecture/...`
```

### B. Mẫu `plan.md`

```markdown
# Implementation Plan: ...

## Summary
## Technical Context
## Constitution Check
## Architecture & Boundaries
## Data & Migrations
## Contracts & MCP Tools
## LLM / Chokepoints
## Test Strategy
| Layer | File | Command |
|---|---|---|
| pure | bridge/tests/pure/test_x.py | `...` |
## QA Gates
- Gate 0: spec + tasks + DoR
- Gate 1: `scripts/e2e-report.sh`
- Gate 1b: `scripts/uat-scenarios.sh`
- Gate 2: UAT sign-off
## Rollout / Rollback / Env
## Docs to update
## Complexity Tracking
```

### C. Mẫu `tasks.md`

```markdown
## Phase 1: Setup
- [ ] T001 ... `Verify: ...`
## Phase 2: US1 — ...
### Tests first
- [ ] T002 [P] [US1] Add failing test ... `Verify: pytest ...`
### Implementation
- [ ] T003 [US1] ... `Verify: ...`
## Phase N: Release
- [ ] T0xx Update docs; `Verify: ...`
- [ ] T0xx Add `## Release note` / `## Production .env setup`
```

### D. `constitution.md` outline

```markdown
# Orchexa Constitution

## Core Principles
I. One core, no tenant taxonomy (P1)
II. SMB first, enterprise by config (P2/P3)
III. One condition context & catalog (P4)
IV. AI signal ≠ fact (P5)
V. All outbound through the gate (P6)
VI. Import/backfill does not trigger (P7)
VII. Version everything (P8)
VIII. Draft → validate → simulate → publish (P9)
IX. Observe & explain (P10)
X. Claude/ChatGPT is the builder brain (P11)
XI. Test-first + behavioral evidence (DoD)
XII. LLM chokepoints (gateway/finalizer/model allowlist)
XIII. Migrations keyed by filename; env names only
XIV. Documentation authority: specs vs docs vs Plane

## Gates
- Gate 0/1/1b/2; `scripts/e2e-report.sh`; UAT sign-off.
## Governance
- Amend via DEC + review; no silent change.
```

### E. `specs/README.md` skeleton

```markdown
# Specs — Feature Execution Layer

- Owner: feature owner
- Source of truth: this folder for feature scope/AC/plan/tasks.
- Product docs: `docs/unicorn-saas-plan/`; engineering docs: `docs/`;
  QA: `docs-e2e/`; status: Plane.
- Naming: `NNN-OSA-<id>-<slug>`; numeric prefix.
- Flow: specify → clarify → plan → tasks → ready → implement → verify → review.
- Do not create plans outside this folder.
```

### F. `specs/INDEX.md` example

| NNN | Slug | OSA | M/W | PRD | Status | Branch | PR |
|---|---|---|---|---|---|---|---|
| 001 | export-csv | OSA-561 | M04/W2 | M04 §5 | Draft | `osa-561-export-csv` | — |

### G. `ROADMAP.md` example

```markdown
# Roadmap

> Index only. Source: docs/unicorn-saas-plan/05-delivery/roadmap-and-milestones.md
> and roadmap/roadmap.json. Do not copy WPs here.

| Wave | Milestone | Specs |
|---|---|---|
| W0 | M0 one branch/contract | — |
| W1 | M1 Edupia parity | ... |
```

### H. `.aiek/adapter.md` planning config example

```yaml
planning:
  mode: speckit
  spec_dir: specs
  task_source: specs/<feature>/tasks.md
  product_docs: docs/unicorn-saas-plan
  qa_docs: docs-e2e
  status_source: plane
```

### I. `docs/README.md` skeleton

```markdown
# Docs map

| Folder | Role | Status |
|---|---|---|
| unicorn-saas-plan | product/portfolio | ACTIVE |
| 02-architecture, 03-guides, 04-api, 04-integrations, 05-sdk, 06-operations, ONBOARDING | engineering | ACTIVE |
| 01-planning | legacy VoiceAgent OS | LEGACY |
| 02-implementation | historical implementation | HISTORICAL |
| superpowers | legacy planner | ARCHIVE |
| qa, uat, verification, evidence | records | ACTIVE |
| ../specs | feature execution | ACTIVE |
| ../docs-e2e | QA process | ACTIVE |
```

---

## 15. Tóm tắt một trang

- **Giữ nguyên** `docs/` Orchexa; **thêm** `specs/` làm lớp feature execution.
- **Một fact, một owner**; link thay vì copy; `ROADMAP.md` mỏng; Plane là status.
- **Spec Kit đủ dữ liệu** nhờ PRD/architecture/QA/case library + adapter + constitution + preset.
- **Không migrate lịch sử**; chỉ archive/legacy marker; pilot 1 feature rồi mới rollout.
- **Phase 2 chưa triển khai**; đây là plan để review và chốt.
