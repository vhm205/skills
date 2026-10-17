# ⚡ Kinetic Brand Film & Manifesto Director Skill

> **Chuyên môn hóa motion graphics, kinetic typography và đạo diễn video thương hiệu nhịp độ cao (Beat-synced High-Voltage Brand Films) sử dụng HyperFrames, GSAP & Tailwind.**

Bộ Skill này được đúc kết từ thực chiến sản xuất video **Orchexa — "Raw Builders" Brand Film (78.5s)**, giải quyết bài toán: **Làm sao biến những tư liệu tĩnh (ảnh chụp chân dung team, ảnh candid, ảnh mockup sản phẩm, terminal code) kết hợp cùng một bài nhạc RAP/Electronic giàu năng lượng thành một video chuyển động ma mị, dồn dập, bám chặt từng nhịp snare và âm tiết của giọng đọc.**

---

## 📂 Cấu trúc thư mục (Skill Repository Structure)

```text
kinetic-brand-film/
├── SKILL.md                          # Sổ tay định nghĩa vai trò & Pipeline 5 giai đoạn cho Agent
├── README.md                         # Tài liệu hướng dẫn sử dụng chi tiết (File này)
└── references/
    ├── motion-patterns.md            # Thư viện code mẫu: Kinetic Slam, Word Slams, Pre-Drop, Matrix Tickers
    ├── camera-and-tracking.md        # Kiến trúc Camera Rig (caption-camera-follow: scale, x, y tracking)
    ├── beat-sync-guide.md            # Sổ tay bắt nhịp nhạc RAP: beat flash, camera shake, rapid exit
    ├── rules-and-pitfalls.md         # Quy tắc sống còn & Bẫy lỗi (Nesting trap, GSAP immediateRender, Face-safe)
    └── template-starter.html         # Boilerplate chuẩn 1920x1080 sẵn sàng code ngay
```

---

## 🎯 Các tính năng & Motion Pattern cốt lõi

### 1. 💥 Syllable-Level Kinetic Slam (`caption-kinetic-slam`)
- Bắt trọn từng âm tiết phát âm (ví dụ: *"A - I"*, *"DOANH NGHIỆP KHÔNG CẦN"*) trên khung Cyber HUD kính mờ (`backdrop-filter: blur(16px)`).
- **Quy tắc Rapid Exit**: Ẩn ngay lập tức trong `0.08s` khi dứt âm tiết vocal để giữ nhịp video luôn nhanh và gãy gọn.

### 2. 🎥 Dynamic Camera Rigging (`caption-camera-follow`)
- Camera ảo điều phối zoom và lia góc (`scale: 1.06 -> 1.10 -> 1.14`, panning `x: ±30px`) bám theo các focal point: Chân dung bên trái ➔ Tôn chỉ bên phải ➔ Dolly-in vào câu punchline trung tâm.
- Giữ mắt người xem luôn tập trung vào điểm nóng mà không làm trôi bố cục.

### 3. 📐 Face-Safe Portrait Framing
- Đóng khung ảnh chân dung trong card chuẩn tỷ lệ `3:4` hoặc `4:5` kèm `object-position: center 25%`.
- Không bao giờ để hiệu ứng hay zoom làm cắt mất đỉnh đầu, mắt hay khuôn mặt của thành viên.

### 4. ⚡ Pre-Drop Hyper Crescendo & Directional Word Slams
- Chữ đập mạnh đa hướng từ Trái, Phải, Dưới theo nhịp Snare.
- Dồn dập 3 tầng chữ tăng dần kích thước và cường độ rung lắc màn hình ngay trước cú Drop cao trào.

### 5. 🛠 Optical Beat Flash & Camera Shake System
- Helper [`addBeatFlash(time, opacity)`](./references/beat-sync-guide.md) tạo xung chớp sáng quang học trên mỗi cú gõ Snare.
- Helper [`addCameraShake(time, intensity)`](./references/beat-sync-guide.md) rung màn hình trên các cú Kick 808 / Drop.

---

## 🚀 Hướng dẫn cài đặt & Kích hoạt

### Cách 1: Sử dụng trong Antigravity CLI / Gemini Code Agent

#### Cài đặt Global (Khuyên dùng - áp dụng cho mọi project trên máy):
Sao chép thư mục skill vào thư mục config của máy:
```bash
mkdir -p ~/.gemini/config/skills/kinetic-brand-film
cp -r /Users/moment/Projects/personal/lab/skills/kinetic-brand-film/* ~/.gemini/config/skills/kinetic-brand-film/
```

#### Cài đặt Local (Chỉ áp dụng cho 1 Repository cụ thể):
Sao chép vào thư mục `.agents/skills/` của project:
```bash
mkdir -p .agents/skills/kinetic-brand-film
cp -r /Users/moment/Projects/personal/lab/skills/kinetic-brand-film/* .agents/skills/kinetic-brand-film/
```

---

## 💬 Mẫu câu lệnh (Prompting Examples)

Sau khi cài đặt, bạn có thể gọi Agent thực hiện video bằng các câu lệnh như sau:

### Ví dụ 1: Tạo mới một video thương hiệu từ đầu
> *"Hãy sử dụng skill `kinetic-brand-film` để dựng một video giới thiệu công ty/sản phẩm dài 60s theo file âm thanh `audio.mp3` và các hình ảnh trong thư mục `assets/`. Bắt nhịp beat chặt chẽ và áp dụng hiệu ứng kinetic slam cho các câu khẩu hiệu."*

### Ví dụ 2: Nâng cấp nhịp độ và thêm hiệu ứng cho video hiện tại
> *"Video hiện tại đang bị chậm và chưa đủ ma mị. Áp dụng các pattern từ skill `kinetic-brand-film`: thêm camera-follow ở Scene 3, thêm pre-drop crescendo trước đoạn drop 45s, và thêm beat flash cho các nhịp snare."*

### Ví dụ 3: Đồng bộ âm tiết RAP (Lyric Sync)
> *"Đoạn 20s - 25s ca sĩ đang rap từng chữ. Hãy áp dụng pattern `caption-kinetic-slam` từ `kinetic-brand-film` để chữ nhảy giật theo từng âm tiết và biến mất ngay khi dứt câu."*

---

## ⚠️ Các quy tắc "Sống Còn" cần nhớ (Critical Rules)

1. **Tránh bẫy lồng thẻ (The Nesting Trap)**: Mọi sub-scene phải là thẻ ngang hàng (`sibling <div>`), không bao giờ lồng scene sau vào bên trong camera-rig của scene trước (tránh lỗi màn hình đen khi rig trước fade out).
2. **GSAP `immediateRender: false`**: Mọi tween `fromTo` xuất hiện sau `0.0s` bắt buộc phải có `{ immediateRender: false }` để tránh lỗi giật hình / render trước.
3. **Khoá thời lượng âm thanh**: Thuộc tính `<div class="composition" data-duration="...">` phải khớp chính xác với kết quả đo của `ffprobe`.

---

## 🧪 Quy trình Kiểm thử & Render Video

```bash
# 1. Kiểm tra cấu trúc HTML và cú pháp HyperFrames (phải đạt 0 lỗi)
npx hyperframes check

# 2. Chụp snapshot kiểm tra các mốc chuyển cảnh then chốt
npx hyperframes snapshot --at 15.0 -o renders/preview_15s.png
npx hyperframes snapshot --at 63.5 -o renders/preview_pre_drop.png

# 3. Xuất video hoàn chỉnh độ phân giải cao (1080p 30fps)
npx hyperframes render -o renders/final_video.mp4
```

---

## 📜 Giấy phép & Tác quyền

Bộ skill được đóng gói bởi **Moment** — Dành cho các dự án nội bộ và open-source thuộc hệ sinh thái video tự động hóa HyperFrames & Motion Design.
