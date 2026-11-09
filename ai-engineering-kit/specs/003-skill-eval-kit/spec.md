# Feature Specification: Skill Eval Kit

**Ngày**: 2026-11-08. **Feature ID**: `003-skill-eval-kit`.
**Delivery scope**: MVP phases 1–3; live pilot phụ thuộc preflight và human outcome labels.

## Mục tiêu

Đo kit có giúp agent hoàn thành công việc tốt hơn baseline, đồng thời chỉ ra chi phí,
độ ổn định và đóng góp của từng thành phần. Mỗi kết luận phải truy về trial và evidence.
Outcome và workflow compliance là hai trục riêng; không dùng cách trình bày riêng của kit
làm điều kiện thắng agent mặc định.

## User Scenarios & Testing

### US1 — So sánh công bằng trên DSH (P1, MVP)

Người phát triển chạy cùng scenario với `no-kit` và `full-kit`, nhận kết quả từng trial,
chênh lệch outcome, compliance và chi phí cùng giới hạn bằng chứng.

Acceptance:
1. Agent sửa đúng bug nhưng không nêu lane vẫn pass outcome; compliance chấm riêng.
2. Agent nêu đủ evidence nhưng code sai hidden test phải fail outcome.
3. Lỗi cài kit, xác thực, timeout hoặc thiếu grader không được chuyển thành pass.
4. Ba scenario × ba lượt × hai cấu hình tạo đúng 18 trial records, kể cả lỗi.
5. Báo cáo còn đủ dữ liệu để chấm lại mà không gọi agent lần nữa.

### US2 — Phát hiện regression và đo ổn định (P1)

Người phát triển so sánh kit ổn định với candidate bằng phiên bản fixture/grader cố định.

Acceptance:
1. Tổng usage/thời gian tính đủ mọi trial; số thiếu dữ liệu không trở thành zero usage.
2. Lỗi nghiêm trọng ở một trial không bị đa số các trial khác che mất.
3. Grader đổi phải tạo phiên bản mới; kết quả cũ giữ nguyên, chấm lại thành report mới.
4. Report khác model, fixture hoặc giới hạn chạy phải hiện mismatch, không tự gộp.

### US3 — Chạy thêm harness và tìm đóng góp từng skill (P2, sau MVP)

Người phát triển dùng cùng contract cho Claude/Codex và sau đó agy/omp; chọn cấu hình
`core + planner` đối chiếu với cùng cấu hình cộng skill mục tiêu.

Acceptance:
1. Adapter khai báo headless/session/skill-events/tool-events/usage/isolation capabilities.
2. Không quan sát skill load không được suy ra không dùng skill.
3. Kết quả tự khai báo và tool event được gắn nhãn độ tin cậy khác nhau.
4. agy/omp chỉ nhận hỗ trợ khi xác minh executable, version, protocol và bằng chứng thực.

## Functional Requirements

- FR-001: Có schema version cho scenario, suite, trial, grading và comparison; validator
  từ chối đầu vào không hợp lệ trước khi gọi model.
- FR-002: Scenario phân assertion thành outcome/compliance/critical; điều kiện bắt buộc
  tách khỏi tiêu chí chất lượng tùy chọn. Thiếu outcome grader phải ghi unavailable.
- FR-003: Mỗi trial có workspace và session mới; hai variant cùng fixture, prompt, model,
  tools, permissions, limits, phản hồi người dùng và chính sách network/dependencies.
- FR-004: Manifest ghi kit revision/content hash, harness/version, model thực tế nếu biết,
  cấu hình, prompt/fixture/grader hashes, trial ID, lịch chạy và nguồn dữ liệu quan sát.
- FR-005: Outcome kiểm bằng grader độc lập sau agent; agent không được sửa oracle,
  expected answers hoặc runner. Kiểm tra grader bằng mẫu đúng, sai và đối kháng.
- FR-006: Ghi transcript, tool events khả dụng, command/exit evidence, diff, artifacts,
  usage và lỗi từng trial; redact secrets trước persist, không lưu raw environment.
- FR-007: Task success không yêu cầu lane/handoff riêng của kit. Critical action violation
  quyết định gate riêng; critical compliance chỉ áp dụng variant có nghĩa vụ tương ứng.
- FR-008: Phân biệt planned, completed, timeout, install/auth/harness/grader error,
  pending-review và unsupported; reported success cần outcome có bằng chứng.
- FR-009: Report có task success, assertion diagnostics, critical violations, coverage,
  thời gian/token/cost và delta từng task. Synthetic và real không được trộn.
- FR-010: Resume chỉ chạy trial chưa thực hiện của cùng manifest; retry tạo attempt mới,
  giữ attempt lỗi và chi phí, không chọn kết quả tốt nhất thay kết quả cũ.
- FR-011: Chấm review/câu hỏi ngữ nghĩa bằng human labels ở MVP; LLM judge chỉ thành
  release gate sau hiệu chỉnh trên nhãn người, rubric và model judge được version hóa.
- FR-012: CI mặc định offline; real run chủ động, có max trials, timeouts và ngân sách.
  Usage thiếu khiến cost cap không thể bảo đảm: phải báo rõ và dùng trial/time limits.
- FR-013: Giữ fixture/report lịch sử; đọc v1 dưới nhãn legacy, không diễn giải điểm cũ
  thành outcome v2. CLI entry points hiện tại tiếp tục hoạt động.

## Scope và defaults

MVP: công cụ phát triển trong source repo; DSH, deterministic graders + human review,
JSON/Markdown reports, ba scenario pilot. Không phát hành npm eval CLI hoặc dashboard.
Không đổi workflow trong core, nội dung skills hay Spec Kit components để làm eval dễ pass.
Mở rộng sau MVP: khoảng 12 task calibration, holdout riêng, regression baseline,
Claude/Codex, ablation; agy/omp theo capability discovery. Không xếp hạng harness khác model.

## Success Criteria

- SC-001: Tất cả acceptance và adversarial grader tests đạt trong offline suite.
- SC-002: Pilot đủ 18 trial records hoặc report incomplete với lý do chính xác; không
  tuyên bố kit tốt hơn khi thiếu dữ liệu, grader chưa hiệu chỉnh hoặc khoảng bất định rộng.
- SC-003: Mọi điểm pass/fail truy được về evidence; aggregate tái tạo được từ trial records.
- SC-004: Không công bố mức pass mới từ mock hoặc report ghép các lần hiệu chỉnh.
- SC-005: Kết quả pilot có thể là cải thiện, không cải thiện hoặc chưa đủ bằng chứng;
  outcome thấp là kết quả nghiên cứu, không phải lỗi của framework.

## References

- Workflow authority: [AGENTS.md](../../AGENTS.md), [documentation ownership](../../core/documentation.md).
- Thiết kế và kiểm chứng: [plan.md](plan.md). Thứ tự công việc: [tasks.md](tasks.md).
- [Agent Skills evaluation](https://agentskills.io/skill-creation/evaluating-skills).
- [Anthropic skill-creator](https://github.com/anthropics/skills/blob/main/skills/skill-creator/SKILL.md).
- [PluginEval và giới hạn](https://github.com/wshobson/agents/blob/main/docs/plugin-eval.md).
