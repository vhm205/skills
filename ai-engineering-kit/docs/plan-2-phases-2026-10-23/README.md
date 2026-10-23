# Plan 2 Phase — AI Engineering Kit → Orchexa Spec Kit

**Ngày:** 2026-10-23
**Nguồn phân tích:** [Đánh giá & đề xuất bộ skills 2026-10-23](../skills-audit-and-plan-2026-10-23.md)
**Trạng thái:** kế hoạch; **Phase 1 đã triển khai** trên nhánh `feat/phase-1-kit-optimization` — **trigger gate PASS** (`dsh` thật 23/25 = 92,0%), **behaviour gate PASS** trên evidence per-scenario cuối cùng (real `dsh` 7/7, 0 critical; raw one-pass 3/7 được giữ nguyên và ghi rõ trong eval report), mock 7/7 chỉ là synthetic — xem [handover Phase 1](../phase-1-handover.md); **Phase 2 mới là plan, chưa triển khai**.

---

## 0. Mục tiêu

1. **Phase 1 — Tối ưu kit:** đưa `ai-engineering-kit` đạt best practice Agent Skills
   (description/triggering, progressive disclosure, scripts, evals, install profile, adapter v2)
   mà **không tạo bộ general skill mới** và không phá workflow.
2. **Phase 2 — Tích hợp Orchexa:** dùng Spec Kit làm lớp feature execution (`specs/`), giữ nguyên
   cấu trúc tài liệu Orchexa (`docs/unicorn-saas-plan`, `docs/`, `docs-e2e`), và bảo đảm Spec Kit
   có đủ dữ liệu (PRD, kiến trúc, QA gate, case library, adapter, constitution) để
   `specify → plan → tasks → implement` chạy đúng.

**Nguyên tắc xuyên suốt:** một fact — một owner; link thay vì copy; không tạo planner thứ hai;
không big-bang; đo trước/sau.

**Trả lời ngắn cho câu hỏi Spec Kit + Orchexa:** Spec Kit là **lớp feature execution** ở
`specs/` (spec/plan/tasks cho từng feature); `docs/unicorn-saas-plan` + `docs/` + `docs-e2e`
vẫn là **lớp tri thức bền vững**; `specs/` **link** tới PRD/kiến trúc/QA, **không copy**.
Spec Kit đủ dữ liệu nhờ 4 nguồn: PRD/roadmap (WHAT/WHY), kiến trúc/API (HOW), adapter +
constitution (command/risk/principle), QA/DoD/case library (acceptance/verify). Chi tiết ở
[Phase 2 §2–4](phase-2-orchexa-spec-kit-integration.md).

---

## 1. Hai phase trong một bảng

| | Phase 1 — Kit optimization | Phase 2 — Orchexa + Spec Kit |
|---|---|---|
| **Mục tiêu** | Kit đạt best practice, có eval/script/profile | Tích hợp Spec Kit vào Orchexa, giữ docs structure |
| **Phạm vi** | `ai-engineering-kit/` | `orchexa-be` (+ `orchexa-fe` khi cần) |
| **Trạng thái** | **Đã triển khai** (`feat/phase-1-kit-optimization`); trigger gate PASS, behaviour gate PASS trên evidence per-scenario 7/7 (raw one-pass 3/7 preserved) | **Chỉ plan, chưa triển khai** |
| **Thời lượng** | 3–4 tuần | 4–6 tuần sau Phase 1 |
| **Đầu ra** | Descriptions, scripts, evals, profiles, adapter v2, docs | `specs/`, `.specify/`, constitution, preset, pilot, docs authority |
| **Không làm** | Không chạm Orchexa | Không migrate lịch sử, không xoá docs, không big-bang |
| **Tài liệu** | [Phase 1 chi tiết](phase-1-kit-optimization.md) | [Phase 2 chi tiết](phase-2-orchexa-spec-kit-integration.md) |

Phase 1 đã chạy hết P1.0–P1.5 trên nhánh `feat/phase-1-kit-optimization`. Trigger gate PASS (`dsh` thật 92,0%); behaviour gate PASS trên evidence per-scenario cuối cùng (real `dsh` 7/7, 0 critical), với raw one-pass 3/7 được giữ nguyên và mọi lần sửa assertion được ghi trong eval report — lưu ý evidence hiện là per-scenario, chưa phải một lần chạy liền mạch 7/7 (checklist release trong handover). Chi tiết và checklist trong [handover Phase 1](../phase-1-handover.md). Gate Phase 2 vẫn phải được chấp nhận trước khi bắt đầu Phase 2.

---

## 2. Thứ tự thực hiện

```text
Phase 0 (đã có)         Phase 1 (3–4 tuần)                  Phase 2 (4–6 tuần)
─────────────────       ─────────────────────               ─────────────────────
Audit 2026-10-23   ──►  P1.0 baseline/checker
                        P1.1 descriptions/format
                        P1.2 workflow correctness
                        P1.3 adapter v2/profile/scripts
                        P1.4 eval/CI
                        P1.5 docs/release
                                │
                                ▼
                        Gate: Phase 1 DoD
                                │
                                ▼
                        P2.0 decisions/prep
                        P2.1 docs authority/legacy freeze
                        P2.2 Spec Kit install/config
                        P2.3 preset/templates
                        P2.4 Orchexa skills/adapter cleanup
                        P2.5 pilot 1 feature
                        P2.6 rollout 2–3 features
```

**Không bắt đầu Phase 2 trước khi Phase 1 đạt DoD**, vì Phase 2 dùng:
`--profile core`, `planning` mode, `speckit-preset` mẫu, `resolve_adapter.py`/`verify.py`/
`worktree.py`, trigger/behavior eval.

---

## 3. Quyết định cần chốt trước khi bắt đầu

| # | Quyết định | Đề xuất | Ai chốt |
|---|---|---|---|
| D1 | Orchexa dùng Spec Kit cho Normal/Large? | **Có**; Small/Infra giữ nguyên | Tech lead + PO |
| D2 | Product plan vẫn là `docs/unicorn-saas-plan`? | **Có**; Spec Kit chỉ là feature layer | PO |
| D3 | `specs/` ở root hay trong `docs/`? | **Root `specs/`** (Spec Kit mặc định; ít ma sát) | Tech lead |
| D4 | Nguồn chuẩn skills: `.agents` hay `.claude`? | **`.agents/` là canonical** (`.agents/skills/`); `.claude/skills/` là mirror tuỳ chọn, nếu cài cả hai thì parity check | Tech lead |
| D5 | `AGENTS.md`/`CLAUDE.md` có được trim? | **Có**; `CLAUDE.md` → `@AGENTS.md`, tách nội dung dài | Tech lead |
| D6 | Harness chính để eval? | **DeepSeek Harness (`dsh`) là chính**; Claude Code/Codex là smoke phụ; script eval harness-agnostic, có `--harness` và mock cho CI | Kit maintainer |
| D7 | Pilot feature nào? | 1 feature nhỏ, không migration/billing/voice | PO + Tech lead |

Nếu D1 = "không", Phase 2 vẫn có thể chạy nhưng chỉ dùng kit `core` cho execution/verification;
không cài `specify`/`specs/`. Khi đó bỏ các phần Spec Kit trong Phase 2.

---

## 4. Tiêu chí thành công

### Phase 1
- 15/15 description có trigger + negative trigger.
- Trigger eval ≥ 90%; behavior eval ≥ 80%; 0 critical safety failure.
- `--profile core|discovery|full`; `core` = 11 skill.
- 4 script (`resolve_adapter`, `verify`, `worktree`, `traceability`).
- Adapter contract v2; `speckit-preset` mẫu; docs authority.
- `check.sh`, `test.py`, `test-speckit.py`, install dry-run PASS.
- 0 file Orchexa thay đổi.

### Phase 2
- `specs/` + `specs/README.md` + `specs/INDEX.md` + `ROADMAP.md` hoạt động.
- `.specify/` + constitution + preset + adapter cài được trong worktree.
- Pilot 1 feature: spec/plan/tasks đủ; implement/verify/review/accept; QA gate; evidence.
- 6 hub skills; 0 frontmatter thiếu; 0 `skill.md`; 0 desc > 1.024; `.claude`/`.agents` parity.
- `AGENTS.md` ≤ 10 KB; `CLAUDE.md` = `@AGENTS.md`.
- Không còn plan mới trong `.planning`/`docs/superpowers`.
- Team Go/No-Go.

---

## 5. Rủi ro cấp chương trình

| Rủi ro | Mức | Giảm thiểu |
|---|---|---|
| Làm Phase 2 trước khi Phase 1 xong → thiếu profile/script/eval | Cao | Gate Phase 1 DoD |
| Tạo planner thứ ba (Spec Kit + Superpowers + .planning + docs) | Cao | Authority matrix + archive marker + chỉ `specs/` cho feature mới |
| Di chuyển docs lớn gây loạn | Cao | Không di chuyển; chỉ mark/index |
| Spec trùng PRD, plan trùng docs | Cao | Spec là slice; link; preset rule |
| Context quá tải (50KB AGENTS + 38 skill) | Cao | Trim AGENTS; core profile; 6 hub |
| Team không dùng | Cao | Pilot + training + đo + điều chỉnh |
| Phase 1 scope creep sang Orchexa | Cao | Gate: Phase 1 chỉ kit |

---

## 6. Không nằm trong plan này

- Migrate toàn bộ lịch sử docs/plans vào `specs/`.
- Xoá `docs/superpowers`, `.planning`, `docs/01-planning`.
- Thay Plane hoặc đổi workflow team ngay.
- Big-bang toàn repo/team.
- Viết lại toàn bộ PRD.

---

## 7. Đọc gì trước

1. [Audit & đề xuất](../skills-audit-and-plan-2026-10-23.md) — lý do, bằng chứng, số liệu.
2. [Phase 1 — Kit optimization](phase-1-kit-optimization.md) — task, file, DoD.
3. [Phase 2 — Orchexa + Spec Kit](phase-2-orchexa-spec-kit-integration.md) — kiến trúc docs,
   authority matrix, preset, pilot.
