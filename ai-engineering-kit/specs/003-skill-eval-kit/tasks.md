# Tasks: Skill Eval Kit

**Input**: [spec.md](spec.md), [plan.md](plan.md).
Thực thi tuần tự theo dependency; không có task yêu cầu agent song song.
Checkbox chỉ đánh dấu phần đã kiểm chứng; evidence ở [execution-log.md](execution-log.md).

## Phase 1 — Contracts và scoring foundation (US1, US2)

- [x] T001 Định nghĩa schemas v2 và validator trong `scripts/_eval/contracts.py`,
  `scripts/_eval/schemas/`; fixture assertions có dimension, required, applicability.
  Verify: malformed manifest, thiếu outcome và unsupported capability được phân loại đúng.
- [x] T002 Viết `scripts/test_evals.py` và golden records trong `evals/tests/` cho outcome
  vs compliance, errors/coverage, unknown usage và critical failures trước khi đổi runner.
  Verify: test mới fail với scoring cũ, pass sau T003.
- [x] T003 Thêm trial-based scoring trong `scripts/_eval/reporting.py`; giữ v1 adapter
  qua `--report-version`, mặc định v2 cho `scripts/eval_tasks.py`.
  Verify: mọi trial/attempt được cộng đúng; majority không thay per-trial result;
  no-kit sửa đúng không fail outcome vì thiếu lane/evidence table.

## Phase 2 — Harness/workspace/evidence (US1)

- [x] T004 Tách adapter dùng chung từ `scripts/eval_trigger.py` sang
  `scripts/_eval/harnesses.py`; lưu capabilities/version/model provenance.
  Verify: fake transcripts cho DSH/Claude/Codex, stream lỗi và usage thiếu; old CLI smoke.
- [x] T005 Thêm `scripts/_eval/workspace.py`: fixture sạch, correct-harness install,
  leakage canaries và manifest hashes.
  Verify: install failure chặn run; global skills không lọt baseline; actual discovery
  phân biệt được no-kit/full-kit; unsupported isolation ghi rõ.
- [x] T006 Thêm `scripts/_eval/runner.py`: schedule seed, limits, process-tree cleanup,
  append-only trial persistence và resume cùng manifest.
  Verify: timeout không để child sống; resume không ghi đè; retry không xóa lỗi.
- [x] T007 Gắn evidence writer/redaction vào runner, lưu raw/normalized events và patch
  trong `evals/results/<experiment-id>/`; điều chỉnh `.gitignore` cho raw local artifacts.
  Verify: fake secrets không xuất hiện trong artifact/log; report tái tạo được offline.

## Phase 3 — Pilot graders và report (US1, US2; MVP)

- [x] T008 Nâng cấp `evals/tasks/03-bug.md`, thêm oracle trong `evals/oracles/` và
  `scripts/_eval/graders.py`; chấm ở bản sạch ngoài agent workspace.
  Verify: đúng fix pass; no-op/hardcode/xóa code/sửa test/config đều bị bắt; repro fail
  trên fixture gốc và pass sau sửa; thiếu process isolation không được release-proof.
- [x] T009 Nâng cấp `evals/tasks/05-review-diff.md`, `04-vague-ticket.md`; tạo blind human
  rubric/label format trong `evals/labels/`.
  Verify: valid paraphrase pass; keyword-only review và câu hỏi vô ích fail;
  chưa có human label thì pending-review, không tự pass.
- [x] T010 Thêm `evals/suites/pilot.json` cho 3 scenarios × 3 repeats × 2 variants,
  model/limits explicit và 18 primary-trial cap.
  Verify: dry-run chỉ planned; manifest thiếu model selection/capability cần thiết bị chặn.
- [x] T011 Xuất JSON/Markdown bằng `scripts/_eval/reporting.py`: outcome/compliance,
  critical/coverage, per-task delta, all-attempt usage/time và limitations.
  Verify: aggregate goldens; synthetic/legacy/manual không lẫn live automated proof.
- [x] T012 Chạy toàn bộ offline checks tại plan.md#verification; sửa regression trước
  live pilot; lưu commands/output trong evidence location của experiment.
  Verify: required checks có exit code và artifacts, skipped checks được giải thích.
<!-- T013 progress 2026-11-09: API-key pilot 18/18 completed; 12 human labels pending.
See execution-log.md and evals/results/pilot-dsh-api-2026-11-09-report.md. -->
- [ ] T013 Xác minh DSH/model/auth, freeze manifest rồi chạy pilot 18 trial; human chấm
  review/vague outputs; xuất report immutable trong `evals/results/`.
  Verify: đủ scheduled records, lỗi giữ nguyên, không chọn best retry, kết luận đúng mức
  evidence; task này thực hiện khi chuyển sang triển khai/live evaluation, không trong planning.

## Phase 4 — Expansion (US2, US3; sau MVP)

- [ ] T014 Mở rộng `evals/tasks/`, `evals/suites/` lên khoảng 12 calibration cases và
  holdout riêng ít nhất 6 cases; giữ dữ liệu/answers khỏi context agent.
  Verify: normal feature đúng planner ownership; infra tools giả lập; clean review và
  preservation cases ngăn false positives; holdout không được dùng tune skill.
- [ ] T015 Thêm stable/candidate và component variants trong contracts/runner;
  thêm paired-by-task bootstrap và reliability summaries trong reporting.
  Verify: mismatch model/fixture/grader bị nêu rõ; intervals từ task clusters;
  không skill-attribution claim khi component dependency chưa được kiểm soát.
- [ ] T016 Xác minh isolation/event capabilities và smoke Claude/Codex qua common adapters.
  Verify: local help/version evidence + real smoke riêng; absence-of-events không thành
  evidence-of-no-skill; không gộp kết quả khác model.
- [ ] T017 Discovery agy/omp, ghi capability matrix và chỉ thêm adapter khi protocol rõ.
  Verify: tên sản phẩm/binary/version/headless/trace/isolation được xác minh; manual
  handoff ghi manual; không sửa global config hay bật hỗ trợ chỉ từ tên integration.

## Phase 5 — Gates và hướng dẫn

- [x] T018 Viết `evals/README.md`, link từ `KIT.md`; nối offline tests vào workflow hiện có
  `../.github/workflows/ai-engineering-kit.yml` tại Git root cha.
  Verify: hướng dẫn chạy từ checkout sạch; mock không cần secrets; CI thực sự discover job.
- [ ] T019 Thêm candidate gate policy vào suite/reporting: zero observed critical,
  coverage requirement, preregistered outcome margin và cost budget.
  Verify: sparse/incomplete evidence trả inconclusive; mock không release-pass;
  framework pass độc lập với việc kit có thắng baseline.
- [ ] T020 Khi cần semantic automation, thêm LLM judge sau human calibration trong
  `scripts/_eval/graders.py`; lưu rubric/model/labels version, cost riêng.
  Verify: blind/order-swapped samples, false-positive review, valid paraphrase và
  unsupported claims; judge không override deterministic failure.

## Dependency và delivery

T001–T003 → T004–T007 → T008–T013 là MVP. T014–T017 mở rộng từ evidence pilot;
T018–T019 hoàn thiện release use. T020 là tùy chọn sau hiệu chỉnh, không chặn MVP.
Không commit/publish/deploy hoặc thay nội dung skills nằm trong yêu cầu lập plan hiện tại.
