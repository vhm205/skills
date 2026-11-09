# Pilot DSH qua API key — 09/11/2026

> Historical snapshot: pilot này chạy trước thay đổi lite/Small inline. Kết quả không đánh giá mã hiện tại; source hashes áp dụng cho snapshot trong manifest gốc.

Đã chạy xong 18/18 lượt thật. Chưa đủ nhãn để kết luận kit tốt hơn mặc định.

## Cấu hình và phạm vi

- DSH `0.2.1-rc.3`, provider khóa ở `deepseek-official`, model yêu cầu `deepseek-flash`.
- Xác thực bằng `DEEPSEEK_API_KEY`; account-login credentials không được chuyển vào agent,
  DSH home mới cho từng lượt, agent không đọc được DSH home gốc.
- Model pin được xác minh từ cấu hình; provider-returned model identity không được báo lại.
- Ba task × ba lần × hai nhóm; cùng fixture/prompt/model/tool boundary, thứ tự theo seed 42.
- Cài toàn bộ kit so với không cài kit. Không cài Spec Kit planner; không đo toàn bộ SDLC
  hoặc đóng góp riêng của một skill. Không tự retry/chọn best run.

## Kết quả outcome

| Task | Mặc định | Có kit | Cách chấm |
|---|---:|---:|---|
| Bug email có dấu `+` | 3/3 pass | 3/3 pass | Oracle riêng + test gốc + kiểm tra preservation |
| Review bỏ kiểm tra tenant | 3 chờ chấm | 3 chờ chấm | Human rubric review-diff/1 |
| Làm rõ “Search must be fast” | 3 chờ chấm | 3 chờ chấm | Human rubric vague-ticket/1 |

Chỉ 6/18 outcomes đã được chấm. Cả hai nhóm đều đạt 3/3 trên task bug;
không diễn giải quality_rate=100% là đạt toàn bộ pilot. Không dùng các giá trị
end-to-end tạm thời để coi 12 kết quả pending là lỗi. Verdict: **inconclusive**.

## Hiệu suất của đợt hợp lệ

| Chỉ số, tổng trên 9 lượt mỗi nhóm | Mặc định | Có kit |
|---|---:|---:|
| Lượt hoàn tất | 9/9 | 9/9 |
| Lỗi harness / timeout | 0 / 0 | 0 / 0 |
| Critical outcome/safety violations quan sát được | 0 | 0 |
| Tổng thời gian trial, gồm setup và chấm | 178.08 giây | 417.14 giây |
| Tổng thời gian agent | 175.86 giây | 409.05 giây |
| Total tokens, gồm cache read | 359,870 | 1,507,120 |
| Input tokens không cache, theo telemetry DSH | 14,894 | 120,416 |
| Cache-read tokens | 324,224 | 1,332,736 |
| Output tokens | 20,752 | 53,968 |

Có kit dùng **4.19× total tokens**, **2.34× thời gian trial** trong mẫu này.
Đây không phải tỷ lệ USD: các loại token có đơn giá khác nhau, chưa có price table xác minh.
Provider cache không được reset giữa các lượt. Chưa báo được chi phí USD đáng tin cậy.

| Task | Thời gian TB mặc định | Thời gian TB có kit | Token tổng mặc định | Token tổng có kit |
|---|---:|---:|---:|---:|
| Bug | 18.24 giây | 70.14 giây | 164,391 | 932,112 |
| Review | 24.81 giây | 30.11 giây | 129,409 | 237,391 |
| Ticket mơ hồ | 16.30 giây | 38.80 giây | 66,070 | 337,617 |

Trace thấy mọi lượt có kit đều gọi skill; không lượt đối chứng nào gọi skill.
Compliance diagnostics đạt ở 9/9 lượt có kit, nhưng một số check là regex/self-report;
đây không phải đánh giá độc lập đầy đủ về chất lượng workflow.

## Sự cố môi trường và chi phí đã tiêu thụ

Đợt đầu bị dừng sau 8 lượt hoàn tất, khi lượt thứ 9 đang chạy: shell/search DSH không tạo
được temp artifacts ngoài writable root của sandbox. Những lượt này không dùng để so sánh
hiệu quả kit. Đã giữ nguyên evidence và [audit đợt hủy](pilot-dsh-api-aborted-2026-11-09.json).

Sửa `TMPDIR`/`TMP`/`TEMP` vào trial root, thêm regression test, bổ sung probe chạy subprocess
runtime thật + bundled ripgrep không gọi model, rồi freeze manifest mới và chạy đủ 18 lượt.
Đợt mới không có lỗi temp nói trên. 39 eval tests và static checks đạt sau sửa.

- Đợt hợp lệ: 1,866,990 tokens đã biết.
- Đợt hủy: 1,305,891 tokens đã biết; usage của lượt bị ngắt chưa có.
- Toàn bộ công việc: **ít nhất 3,172,881 tokens**, bao gồm cache-read; chi phí USD chưa xác định.

Đợt hủy là lỗi môi trường của runner, không phải lỗi chất lượng skill/model và không bị
ẩn khỏi accounting. Hai experiment dùng manifest khác nhau, không trộn outcome.

## Bằng chứng và bước cần người thực hiện

- [Gói 12 câu trả lời để chấm, không ghi variant](pilot-dsh-api-2026-11-09-human-review.md).
- [Labels copy chưa điền](pilot-dsh-api-2026-11-09-human-labels.json): chỉ người chấm điền
  passed/reviewer/evidence, giữ trial ID/hash/rubric. Regrade không gọi model.
- [JSON report](pilot-dsh-api-fixed-2026-11-09.json) và
  [Markdown report máy sinh](pilot-dsh-api-fixed-2026-11-09.md).
- [Execution/provenance audit](pilot-dsh-api-2026-11-09-execution.json), gồm manifest hash.
- Evidence local bất biến: `evals/results/local/pilot-dsh-api-fixed-2026-11-09/` (Git ignored).
  Đã kiểm tra 18 artifact hashes và source hashes vẫn khớp manifest.

Remote CI, independent review và npm checks chưa chạy trong lượt này. Chưa commit/push.
T013 còn mở cho tới khi có human labels. Sau chấm, cần thêm case khó và holdout trước khi
đưa ra claim hiệu quả toàn bộ kit hay từng skill.
