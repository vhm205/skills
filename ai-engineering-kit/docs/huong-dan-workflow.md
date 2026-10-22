# Hướng dẫn dùng AI Engineering Kit

Kit này trả lời đúng một câu hỏi cốt lõi: **với việc hiện tại, bước tiếp theo là gì và điều gì sẽ
chặn lại nếu chưa đủ điều kiện.**

Kit gồm 15 skill. Bạn không cần nhớ hết, chỉ cần nắm rõ **ba câu hỏi đầu vào** và **ba cổng
chặn**.

---

## 1. Bản đồ một trang

```
            VIỆC ĐẾN
               │
   ┌───────────┴────────────┬──────────────────────┐
   │                        │                      │
Có ticket kèm AC?     Chưa biết CÓ NÊN làm?   Biết nên làm,
   │                        │                 chưa rõ LÀM SAO?
   ▼                        ▼                      ▼
intaking-ticket        exploring-idea         shaping-feature
   │                        │                      │
AC không kiểm được     DROP / ASSESS /        Feature Brief
→ BLOCKED, hỏi PO      NEEDS DECISION              │
   │                        │                      │
   └────────────┬───────────┴──────────────────────┘
                ▼
        PHÂN LOẠI LÀN  (classification.md)
                │
   ┌────────┬───┴────┬──────────┐
   │        │        │          │
 SMALL   NORMAL    LARGE      INFRA
   │        │        │          │
   │   specify   specify+   shipping-
   │   plan      research   infrastructure
   │   tasks     worktree
   │        │        │          │
   └────────┴────┬───┴──────────┘
                 ▼
         executing-task  (+ TDD, systematic-debugging)
                 ▼
         verifying-change        ← CỔNG 1: không có bằng chứng tươi thì không xong
                 ▼
         reviewing-change
                 ▼
         authoring-pr            ← bắt buộc self-review trước khi nhờ người khác
                 ▼
         accepting-change        ← CỔNG 2: UAT / bằng chứng vận hành + ký duyệt
                 ▼
               DONE
```

---

## 2. Tra nhanh: bạn đang ở tình huống nào

| Bạn nói / nhận được | Dùng skill |
|---|---|
| "Có nên làm cái này không?" · "Khách than phiền X" · một ý tưởng chưa rõ hình thù | `exploring-idea` |
| "Chốt làm rồi, nhưng chưa rõ nó hoạt động thế nào" | `shaping-feature` |
| Một ticket từ tracker, có User Story + AC + BR | `intaking-ticket` |
| Dự án mới tinh, chỉ có BRD | `shaping-project` |
| "Sửa lỗi chính tả ở email đăng ký" | phân loại SMALL → `executing-task` |
| "Thêm xuất CSV cho trang báo cáo" | NORMAL → Spec Kit `specify` → `plan` → `tasks` |
| "Đổi sang tính tiền theo mức dùng" | LARGE → research → spec → NEEDS DECISION → worktree |
| "Chuyển staging lên cụm mới" · "Build image theo sha" · "Đo tải bằng k6" | INFRA → `shipping-infrastructure` |
| "Cái này hỏng mà không hiểu vì sao" | `systematic-debugging` |
| "Viết test trước đi" · fix bug | `test-driven-development` |
| "Làm song song mấy việc này được không?" | `using-worktrees` + `parallel-development` |
| "Xong chưa?" | `verifying-change` — và chỉ nó mới được trả lời |
| "Review giúp" · nhận feedback review | `reviewing-change` |
| "Mở PR đi" | `authoring-pr` |
| "Release được chưa?" | `accepting-change` |
| "Merge / đóng nhánh" | `finishing-branch` |

---

## 3. Từng skill: dùng khi nào, và dừng ở đâu

### Nhóm khám phá — cả ba đều DỪNG, không được viết code

| Skill | Dùng khi | Ra cái gì | Dừng ở đâu |
|---|---|---|---|
| **exploring-idea** | Chưa biết **có nên** làm hay không (kể cả quyết định kiến trúc chưa có mặc định). | Idea Note: vấn đề · đối tượng chịu ảnh hưởng · bằng chứng · 3-5 hướng giải quyết (**luôn kèm hướng "không làm gì"**). | Đúng 1 trong 4 kết luận: DROP / SHAPE / ASSESS / NEEDS DECISION. |
| **shaping-feature** | Đã chốt làm, nhưng chưa rõ **làm thế nào**. | Feature Brief ngắn gọn trong một trang. | Viết xong brief là dừng. Không lập plan, không viết code. |
| **intaking-ticket** | Đầu vào là ticket có sẵn AC. | Phân loại từng AC thành: máy kiểm được / người kiểm được / **chưa kiểm được**. Kèm bảng truy vết `AC ↔ BR ↔ tầng test ↔ UAT case`. | Còn AC "chưa kiểm được" ⇒ **BLOCKED**, chuyển câu hỏi cho PO. Không tự đoán mò. |
| **shaping-project** | Dự án mới, chỉ có BRD. | Project Brief. | Dừng lại. Việc lên roadmap thuộc phạm vi của Spec Kit. |

> **Đây là giá trị lớn nhất của kit.** Ba điểm dừng này tồn tại để ngăn việc nhảy thẳng từ "ý
> tưởng mơ hồ" sang viết code.

Chọn nhầm skill là lỗi rất hay gặp. Phân biệt nhanh:

```
"chưa biết CÓ NÊN làm không"    → exploring-idea
"biết nên làm, chưa rõ LÀM SAO" → shaping-feature
"có AC rồi nhưng AC mơ hồ"      → intaking-ticket
```

### Nhóm thực thi

| Skill | Dùng khi | Điểm cốt lõi |
|---|---|---|
| **executing-task** | Đã có nguồn sự thật rõ ràng (`tasks.md` hoặc một việc SMALL cụ thể). | Làm **đúng** những gì nguồn sự thật nêu. Không tự ý mở rộng. |
| **systematic-debugging** | Có lỗi nhưng **chưa chứng minh được nguyên nhân**. | Xem mục 5 bên dưới — đây là skill có nhiều cổng kiểm soát nhất. |
| **test-driven-development** | Adapter bật `tdd: required`, khi fix bug, hoặc khi code nhiều logic. | Viết test đỏ ở **tầng thấp nhất chứng minh được hành vi**; bắt buộc phải **thấy test đỏ** trước khi sửa. |
| **shipping-infrastructure** | Hạ tầng, pipeline build, deploy, release, đo tải. | **Luôn xếp vào LARGE.** Bằng chứng là trạng thái hệ thống quan sát được, không phải test đỏ. |
| **using-worktrees** | Việc LARGE, hoặc cần chạy song song. | Tạo checkout riêng biệt cho từng việc. |
| **parallel-development** | Nhiều việc thật sự độc lập. | Chỉ chạy song song khi thỏa mãn cả 5 quy tắc độc lập. |

### Nhóm chứng minh và bàn giao

| Skill | Dùng khi | Luật cứng |
|---|---|---|
| **verifying-change** | Trước **mọi** lời tuyên bố "xong". | Nếu chưa chạy lại lệnh kiểm chứng trong phiên này sau lần sửa cuối cùng, **tuyệt đối không được nói là đạt**. |
| **reviewing-change** | Sau khi verify, trước khi hoàn tất. | Việc LARGE bắt buộc phải có người review độc lập. |
| **authoring-pr** | Trước khi nhờ người khác đọc. | Số liệu kiểm thử phải **copy nguyên văn**, giữ đủ cả fail/skip. Nếu thiếu bằng chứng thì ghi "còn thiếu", **cấm bịa ảnh**. |
| **accepting-change** | Trước khi release. | `product` = phiếu UAT kèm chữ ký · `ops` = smoke test + so sánh trước/sau + **phương án rollback đã diễn tập**. |
| **finishing-branch** | Khi được yêu cầu merge hoặc đóng nhánh. | Chỉ thực hiện sau khi tất cả đã xanh. |

---

## 4. Ba luật xuyên suốt

**1 · Một plan duy nhất.** Sau khi chạy `specify`, thư mục `specs/<feature>/` là plan DUY NHẤT.
Plan sai thì sửa trực tiếp vào đó; không tạo file plan thứ hai và không trao đổi plan rời rạc
trong chat.

**2 · Không có bằng chứng tươi thì không có "xong".** "Chắc là chạy được" không phải là xong. Nếu
adapter khai báo `baseline`, trạng thái *xanh* nghĩa là **không phát sinh thêm lỗi đỏ so với
baseline**, không nhất thiết là 0 lỗi. **Cấm nới lỏng assertion để cho xanh.**

**3 · Chỉ có ba kiểu bàn giao cho người.** Ngoài ba trạng thái này, agent phải tự động tiếp tục xử
lý:

| | Khi nào |
|---|---|
| **BLOCKED** | Đi tiếp là phải đoán mò, có nguy cơ gây hỏng, hoặc vượt thẩm quyền (bao gồm cả trường hợp "đã fail 3 lần"). |
| **NEEDS DECISION** | Cần đánh đổi về mặt sản phẩm hoặc kiến trúc ngoài phạm vi của agent. Bắt buộc kèm bảng đánh đổi và chi phí rủi ro nếu chọn sai. |
| **DONE** | Đã verify xong và có đầy đủ bằng chứng kiểm thử. |

---

## 5. Vòng fix bug, chi tiết

Đây là quy trình chạy nhiều nhất và cũng dễ vấp bẫy nhất.

```
Phase 0 · NHẬN TIN   ← thiếu thì HỎI, không điều tra
   Khi nào · môi trường nào · vào đâu · các bước kèm DỮ LIỆU THẬT ·
   thấy gì (nguyên văn) · mong đợi gì · mức độ + tần suất · bằng chứng (trace id…)

Phase 1 · TÌM NGUYÊN NHÂN
   Có trace id thì ĐỌC TRACE TRƯỚC khi tái hiện — rẻ hơn nhiều
   Truy ngược từ giá trị sai về nơi nó sinh ra

Phase 2-3 · SO SÁNH VỚI CÁI ĐANG CHẠY ĐÚNG → GIẢ THUYẾT VIẾT RA GIẤY

Phase 4 · VÁ
   Test đỏ tái hiện trước → vá tại gốc → xanh

Phase 5 · BẢN VÁ ĐANG CHẠY CHƯA?        ← bước hay bị bỏ nhất, tốn tiền nhất
   Restart/rebuild chưa · asset bump version chưa · migration áp chưa ·
   index build lại chưa · đúng môi trường chưa
   ⚠ KIỂM TRA BẰNG CÁCH MỞ TIẾN TRÌNH MỚI thì LUÔN cho kết quả sai —
     tiến trình mới nạp code mới bất kể tiến trình đang phục vụ chạy gì.
     So thời điểm khởi động của tiến trình đang chạy với mtime của file.

Phase 6 · ĐĂNG KÝ REGRESSION
   Test phải nằm trong làn CI thật sự chạy nó.
   CI chạy theo DANH SÁCH FILE thì phải thêm file vào danh sách —
   không thêm thì CI không chạy mà vẫn báo xanh.

Ba lần vá không xong ⇒ DỪNG, báo BLOCKED. Không vá chồng lên nhau.
```

**Năm họ lỗi không có stack trace** (chi tiết trong `systematic-debugging/references/`):

1. Bản vá **tồn tại** trong code nhưng không **đang chạy** trên hệ thống.
2. `try/except` quá rộng nuốt lỗi ⇒ bản vá trở thành no-op.
3. Bên ghi và bên đọc dùng **tên khác nhau** — dù cả hai bên đều báo "thành công".
4. "Tầng đọc không thấy X" **không** đồng nghĩa với "nguồn không có X".
5. Một giá trị định danh bị **tự sinh ra** thay vì **tra cứu** — trông hợp lý nhưng sai hoàn toàn.

---

## 6. Năm kịch bản thật

**Fix bug từ QA**
`systematic-debugging` (Phase 0 → 6) → `test-driven-development` → `executing-task` →
`verifying-change` → `authoring-pr` → `accepting-change`

**Enhance feature từ ticket**
`intaking-ticket` (Cổng 0) → `specify` → `plan` → `tasks` → mỗi task TDD →
`verifying-change` → `reviewing-change` → `authoring-pr` → `accepting-change`

**Request mơ hồ**
`exploring-idea` → *(dừng, người chốt)* → `shaping-feature` → *(dừng)* →
`intaking-ticket` → `specify`

**Feature mới từ brief**
`shaping-feature` → `specify` → `plan` → NEEDS DECISION → `tasks` → `using-worktrees` →
TDD + `executing-task` → `verifying-change` → review **độc lập** → `authoring-pr` →
`accepting-change`

**Hạ tầng / CI-CD**
`exploring-idea` → NEEDS DECISION → quyết định ghi vào `plan.md` dạng ADR →
`shipping-infrastructure` → `verifying-change` → `accepting-change` (ops)

---

## 7. Adapter: nơi chứa mọi thứ riêng của dự án

Skill cố tình **không biết** dự án của bạn. Mọi lệnh test, đường dẫn, vùng rủi ro và quy ước PR
đều nằm gọn trong một file duy nhất: `.aiek/adapter.md`.

Adapter được phép: khai báo lệnh, thêm `risk_areas`, bắt buộc TDD, bắt buộc người review, và
**định tuyến** ("triệu chứng X thì gọi playbook Y sẵn có của dự án").

Adapter **không** được phép: thêm bước mới, đổi tên handoff, tạo artifact plan thứ hai, hoặc miễn
trừ việc verify. Rủi ro chỉ được tăng, không được giảm.

Kit có sẵn `adapters/default` (tự dò lệnh) và `adapters/orchexa`.

---

## 8. Mười lỗi hay gặp

1. Nhảy từ ý tưởng mơ hồ thẳng sang viết code — bỏ qua cả ba điểm dừng khám phá.
2. Tự suy đoán rồi điền AC còn thiếu để làm tiếp, thay vì hỏi lại PO.
3. Chạy đủ bộ Spec Kit cho một việc sửa chính tả (và ngược lại: chạy migration mà không có spec).
4. Tuyên bố "xong" khi chưa chạy lại lệnh kiểm chứng trong phiên này.
5. Nới lỏng assertion hoặc skip test chỉ để cho CI xanh.
6. Viết test sau khi code mà **chưa bao giờ thấy nó đỏ** — test đó chưa chứng minh được gì.
7. Thêm test mới nhưng quên đăng ký vào làn CI ⇒ xanh giả.
8. Sửa xong không restart/rebuild, rồi vội kết luận "fix không hiệu quả".
9. Kiểm tra bản vá bằng cách mở tiến trình mới — cách này luôn cho kết quả sai.
10. Mở PR ghi chung chung "all tests pass" mà không có lệnh chạy và con số thực tế.

---

## 9. Đọc thêm

| Cần gì | Đọc |
|---|---|
| Workflow chuẩn đầy đủ | `core/WORKFLOW.md` |
| Phân loại làn SMALL/NORMAL/LARGE/INFRA | `core/classification.md` |
| Mẫu BLOCKED / NEEDS DECISION / DONE | `core/handoffs.md` |
| 5 quy tắc chạy song song | `core/parallelism.md` |
| Cách viết adapter cho dự án mới | `core/adapter-contract.md`, `docs/adding-an-adapter.md` |
| Cài vào một dự án | `README.md` |
