# Implementation Plan: Skill Eval Kit

**Ngày**: 2026-11-08. **Spec**: [spec.md](spec.md). **Lane dự kiến**: LARGE,
do thay đổi phép đo, chạy subprocess và ranh giới workspace/grader.

## Summary

Mở rộng hai Python runners hiện có, giữ entry points; tách logic dùng chung thành
`scripts/_eval/`. Giao MVP DSH trước; outcome, compliance và hiệu quả báo riêng.
Đây là kế hoạch triển khai, không xác nhận tính hiệu quả của kit.

## Technical Context

Python chuẩn thư viện cho runner/graders/reports; unittest cho kiểm chứng offline.
Fixtures có thể dùng runtime riêng trong evals, không đưa project facts vào skills.
Không thêm thư viện orchestration, database hoặc UI trong MVP.

Quan sát source ngày lập plan:
- `scripts/eval_tasks.py` dùng assertion regex/filesystem và chấm chung mọi assertion.
- `run_all` dùng majority; tổng usage/thời gian lấy từ record đại diện thay vì mọi trial.
- Behavior installer chưa truyền harness đích; install failure chưa được chặn ngay trước run.
- Isolation hiện chủ yếu đặt `DSH_AGENTS_HOME`; cần xác minh cả parent instructions,
  global skills, hooks, memory, cấu hình và credentials cho từng harness.
- Git root là thư mục cha `skills/`; CI hiện có tại
  `../.github/workflows/ai-engineering-kit.yml`, gồm quick/nightly mock jobs.
  Nối eval tests vào workflow đó; không tạo `.github/` lồng trong kit.
- Chưa xác minh live CLI/model/credentials. Không coi thông tin source là live support proof.

## Constitution Check

Plan/spec/tasks chỉ có ở feature này; không tạo bản plan khác trong docs hoặc skill.
Scaffold dùng upstream Spec Kit create-new-feature/setup-plan trong scratch project;
repo hiện tại không bị init lại, đổi branch hoặc sửa integration. Chưa chạy full
specify/clarify/analyze workflow và không tuyên bố đã qua các gate đó.
Không sửa core, skills, adapters hoặc speckit để phù hợp grader. Nếu sau này đổi installer,
phải đồng bộ bash/TypeScript và kiểm tra byte parity theo AGENTS.md.

## Project Structure và ownership

| Path dự kiến | Trách nhiệm |
|---|---|
| `scripts/eval_tasks.py`, `scripts/eval_trigger.py` | CLI tương thích, điều phối; không giữ logic harness trùng |
| `scripts/_eval/contracts.py`, `schemas/` | Runtime validation và JSON schemas v2 |
| `scripts/_eval/harnesses.py` | Adapter chung, capability detection, event normalization |
| `scripts/_eval/workspace.py`, `runner.py` | Install, isolation, limits, trial lifecycle |
| `scripts/_eval/graders.py`, `reporting.py` | Kiểm chứng độc lập, aggregate từ mọi trial |
| `scripts/test_evals.py`, `evals/tests/` | Contract, fake harness, golden aggregate, adversarial tests |
| `evals/suites/`, `evals/oracles/`, `evals/labels/` | Suite definitions, grader riêng, human labels |
| `evals/tasks/` | Nâng cấp fixture có version, giữ lịch sử |
| `evals/README.md` | Cách chạy và đọc số; viết khi triển khai, link spec thay vì chép plan |
| `evals/results/<experiment-id>/` | Evidence artifacts; local mặc định, chỉ check in báo cáo đã redact |

Eval chạy trong source checkout. Chưa đưa vào npm hoặc cây cài của consumer;
`package.json#files`, `src/install.ts`, `scripts/install.sh` giữ nguyên trong MVP.

## Phase 1 — Contracts và phép đo, prerequisites của MVP

1. Schema v2: Experiment → Variant → Scenario → Trial → AssertionResult. Mỗi trial là
   record bất biến; regrade tạo report mới gắn cùng artifact hashes.
2. Variant MVP là no-kit/full-kit. Legacy `--both` ánh xạ hai variant này; thêm
   `--report-version 1|2`, mặc định v2; v1 là compatibility view, gắn nhãn legacy.
   Fixture v1 đọc được nhưng thiếu outcome sẽ unavailable, không tự đoán từ regex.
3. Chốt outcome required, compliance required/optional, critical violation và applicability.
4. Chốt denominator: completed-success/graded-completed là quality rate có coverage đi kèm;
   completed-success/all-started là end-to-end rate, timeout/error không thành công.
   Pending/planned không tính success. Báo planned/started/completed/graded/errors riêng.
5. Giữ mọi trial; majority chỉ diagnostic. Cost/time sum tất cả attempts; usage thiếu là
   null + coverage, không zero. Tiền chỉ tính từ price table có version và usage đủ loại
   input/output/cache; phí judge tách khỏi agent.

Exit: mẫu agent sửa đúng nhưng thiếu lane pass outcome; code sai với report đẹp fail;
synthetic, planned và errors không được lọt vào real success aggregates.

## Phase 2 — Workspace, harness và evidence

1. Dùng adapter chung cho cả trigger/task; kiểm tra version/capabilities trước run.
2. Fresh workspace mỗi trial; isolated config root theo harness, giữ authentication bằng
   cơ chế được CLI hỗ trợ, không thay global config hoặc copy secrets vào evidence.
3. Truyền đúng harness cho installer; stop trial khi install thất bại. Full-kit variant
   ghi đúng thành phần cài; planner chỉ được coi installed khi thực sự có artifacts.
4. Xác minh global-skill canary và instruction/config leakage. Temp directory tự nó
   không phải sandbox: chỉ chạy fixture tin cậy; nếu không ngăn agent đọc oracle ở host,
   ghi grader isolation unsupported và không dùng làm release proof.
5. Parent runner giữ oracle/expected labels ngoài workspace; chạy kiểm chứng sau agent
   trong bản sạch ghép patch với tests gốc, không tin tests/config agent đã chỉnh.
6. Mỗi trial lưu manifest, normalized events, transcript, patch, artifacts, grader outputs,
   usage, command/exit evidence; hạn chế file size và redact trước ghi.
7. Timeout/cancel kết thúc cả process tree. Trial budget tính probes/retries riêng và rõ;
   không auto retry lỗi. Lịch cặp A/B xen kẽ, randomized theo seed được lưu.

Exit: fake harness không vượt workspace/timeout; install/auth/stream errors đúng loại;
resume từ interrupted experiment không ghi đè hoặc chạy lại trial đã hoàn tất.

## Phase 3 — Pilot outcome graders và báo cáo MVP

Ba scenario đầu: `bug`, `review-diff`, `vague-ticket`.
- Bug: grader chạy known-failing repro trước, hidden tests sau; kiểm tra baseline tests và
  protected files. Controls gồm no-op, fix đúng, hardcode, xóa code, sửa tests/config.
- Review: gold finding mô tả lỗi thật và vị trí; human chấm đúng nguyên nhân, ảnh hưởng,
  vị trí và false positives. Từ khóa tenant/IDOR tự nó không đủ pass.
- Vague ticket: human chấm câu hỏi có thu hẹp điều kiện thành công, file diff chứng minh
  không sửa code thiếu cơ sở; không bắt buộc literal BLOCKED hoặc số dấu hỏi cho outcome.
- Trace không đủ chứng minh test-before-fix hoặc command execution thì compliance unknown;
  không suy ra đã làm từ câu trả lời cuối.

JSON + Markdown: paired per-task outcome, compliance, critical violations, reliability,
coverage, cost/time/token, human interventions và limitations. Human-required trials giữ
pending-review đến khi label được nhập. Rubric và labels version hóa, blind variant labels.

Chạy 18 trial trên DSH chỉ sau khi offline checks đạt và xác định model/limits trước run.
Plan đề xuất trần 18 primary trials, 900 giây/trial; tối đa 4,5 giờ agent execution cộng
setup/grading. Tiền chưa ước lượng vì chưa xác minh model/usage pricing. Lỗi không được
thay bằng lượt thuận lợi; report incomplete/failed trials rồi quyết định experiment mới.

Exit MVP: framework được kiểm chứng, đủ evidence cho mọi trial đã chạy, report có audit
của người. Không yêu cầu kit thắng baseline để coi framework hoạt động đúng.

## Phase 4 — Regression, holdout và thêm harness

1. Khoảng 12 calibration task; mở rộng typo, normal feature, infra/no-deploy, preservation,
   multi-turn, review clean diff, negative triggers, failure recovery, documentation.
2. Holdout ban đầu ít nhất 6 task khác về lỗi/context; không chỉ paraphrase calibration.
   Không để answers/graders trong agent context; task đã dùng chỉnh skill chuyển khỏi holdout.
3. Đóng băng suite trước benchmark. Chấm lại toàn bộ candidate/baseline bằng cùng grader;
   không ghép các lượt thuận lợi qua nhiều phiên bản fixture.
4. So stable-kit/candidate; thêm core/planner ± skill bằng explicit component manifests,
   cùng dependency closure. Nếu chưa tách được component thì không tuyên bố skill attribution.
5. Báo per-trial success, all-trials-success theo task; pass@k/pass^k là secondary với
   sample counts/assumptions. Paired bootstrap resample theo task, không coi repeats độc lập.
6. Claude/Codex thêm probe và transcript contract tests rồi smoke. Codex dùng documented
   noninteractive JSON interface; flags/isolation phải đối chiếu help của CLI cài thực tế.
7. agy/omp discovery xác nhận tên sản phẩm, executable, headless/protocol/isolation.
   Có thể manual handoff; kết quả ghi manual, không coi tương đương automated runner.

Exit: capability matrix có evidence, per-harness reports; không gộp model/config khác nhau.

## Phase 5 — CI, hướng dẫn và release gate

Offline CI: schema/unit/adversarial/fake-harness/aggregate/mock checks; không secrets.
Mở rộng `../.github/workflows/ai-engineering-kit.yml`; giữ path filters hiện có.
Real suite: chạy chủ động trên trusted runner, lưu manifest và artifacts đã redact.
MVP không có LLM judge tự động. Đợt sau thêm judge chỉ khi đối chiếu human labels,
kiểm tra order bias, unsupported claims và false positives; judge không override hard fail.

Gate framework: tất cả required checks đạt; oracle/isolation/persistence invariants đúng.
Gate candidate kit: zero observed critical violations, đủ coverage và outcome không giảm
quá margin đã chốt trước experiment. Margin mặc định zero; interval thiếu lực thống kê
thì verdict inconclusive, không tự pass. Cost budget và minimum worthwhile gain là tham số
experiment; chưa có dữ liệu thì không chốt ngưỡng 80/90% hoặc gắn badge chất lượng.
Không quan sát vi phạm trong bộ mẫu nhỏ không chứng minh rủi ro bằng zero.

## Verification

Khi triển khai từng phase: red/green tests ở lớp thấp nhất cho scoring, isolation,
process lifecycle và oracle integrity. Không gọi model trong unit tests.

Required implementation commands:
```bash
python3 scripts/test_evals.py
python3 scripts/test.py
python3 scripts/test_scripts.py
python3 scripts/eval_trigger.py --mock
python3 scripts/eval_tasks.py --mock
scripts/check.sh
python3 scripts/check_skills.py . --kit . --require-trigger
scripts/install.sh /tmp/aiek-eval-kit-check --dry-run
```

Nếu chạm installer/Spec Kit: thêm `python3 scripts/test-speckit.py`, parity/package checks.
Nếu chạm TypeScript/UI/npm: thêm `npm run check` và `npm run test:package`.
Live run là bằng chứng riêng; mock/checker/build không chứng minh agent hiệu quả.

## Risks và rollback

- Metric drift: schema/grader/suite hashes, golden reports; không overwrite evidence cũ.
- Data leakage: fixture canary + process boundary; hạn chế claim khi capability thiếu.
- Khác model/harness: phân tầng, không suy ra thay đổi do skill khi nhiều biến cùng đổi.
- Tốn token: pilot trước, no automatic retry; ngân sách USD hard cap chỉ khi có telemetry đủ.
- Semantic bias: human blind labels trước, judge calibration sau; hỗ trợ valid paraphrases.
- Compatibility: giữ v1 view và entry points; rollback code không xóa artifacts v2.

## Sources

- [Agent Skills](https://agentskills.io/skill-creation/evaluating-skills).
- [Anthropic skill-creator](https://github.com/anthropics/skills/blob/main/skills/skill-creator/SKILL.md).
- [PluginEval limitations](https://github.com/wshobson/agents/blob/main/docs/plugin-eval.md).
- [OpenAI Codex noninteractive execution](https://learn.chatgpt.com/docs/developer-commands#codex-exec),
  đọc qua OpenAI developer docs MCP ngày 2026-11-08; local capability probe vẫn bắt buộc.
