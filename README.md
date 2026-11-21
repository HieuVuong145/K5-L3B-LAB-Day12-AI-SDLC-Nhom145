# Day 12 — AI SDLC: Quán Ăn Chợ Nổi (Nhom145)

> **Nhóm 2 người** (Vương Toàn Minh Hiếu & Nguyễn Đình Trường, đã phê duyệt) · Phát triển game 2D qua **4 phase** theo chuẩn AI-SDLC: Út Sen lặn bắt cá, hái bông điên điển buổi sáng, tối mở quán phục vụ khách trên nhà bè Má Tư.

---

## 1. Yêu cầu môi trường & Bắt đầu nhanh (≤ 3 lệnh từ clone sạch)

- **Môi trường:** Python 3.10+ (macOS / Linux / Windows). Game chỉ dùng thư viện chuẩn của Python, **không cần cài đặt thư viện bên ngoài**.
- **Chạy từ clone sạch trong 3 lệnh:**

```bash
git clone https://github.com/HieuVuong145/K5-L3B-LAB-Day12-AI-SDLC-Nhom145.git && cd K5-L3B-LAB-Day12-AI-SDLC-Nhom145
PYTHONPATH=tests:. python3 -m unittest discover -s tests -v
python3 -m chonoi.live --mode gather
```

Mở trình duyệt tại địa chỉ in ra (mặc định `http://127.0.0.1:8000/`) để trải nghiệm trực tiếp.

---

## 2. Cách chơi & Phím điều khiển

- **Chế độ Buổi sáng (`gather`):**
  - Chạy: `python3 -m chonoi.live --mode gather [--inventory-out kho.json]`
  - `WASD` hoặc `phím mũi tên`: Bơi (độ sâu $d$ tăng khi lặn xuống).
  - `E`: Cập bến (ở mạn thuyền bên trái) hoặc Hái nút cây trên mặt nước ($d \le 0.5\,\text{m}$).
  - `Space`: Bắt cá khi lặn dưới nước ($d > 0.5\,\text{m}$).
  - `H` (hoặc click nút HUD): Bật/tắt **Chế độ tương phản cao** (High Contrast Mode).
  - `R`: Chơi lại từ đầu.
- **Chế độ Buổi tối (`quan`):**
  - Chạy: `python3 -m chonoi.live --mode quan --inventory docs/contracts/inventory.sample.json`
  - `WASD`: Đi lại trong quán bè.
  - `E`: Tương tác với Bếp B1/B2 (nấu món, nhấc món chín) và Bàn T1–T4 (phục vụ khách).
  - `C`: Đóng ca sớm nếu muốn kết toán ngay.
  - `H`: Bật/tắt chế độ tương phản cao.
- **Chế độ Ngày trọn vẹn (`day`):**
  - Chạy: `python3 -m chonoi.live --mode day`
  - Đi qua chu kỳ hoàn chỉnh: `gather -> quan -> shop`, tích lũy tiền và mua nâng cấp oxy / máu tại Tiệm Chú Sáu.

---

## 3. Hệ thống cảnh báo dễ nhận biết & Chế độ tương phản cao

1. **Thủy quái gần:** Biểu tượng và viền tím/vàng cảnh báo `⚠️ CÁ SẤU ĐANG ĐẾN GẦN! 🐊` khi Cá Sấu Năm Chèo tiến vào cự ly nguy hiểm.
2. **Oxy sắp hết & Hết hơi:** Thông báo nổi bật `⚠️ OXY SẮP HẾT! 🫧 (Hãy nổi lên ngay)` khi oxy còn dưới 5 giây, và `🚨 HẾT OXY! 🚨 (ĐANG BỊ NGẠT)` khi thanh oxy cạn kiệt.
3. **Khách sắp giận:** Huy hiệu màu đỏ `⚠️ KHÁCH SẮP GIẬN! 💢 Bàn <T>` khi thanh kiên nhẫn của khách giảm xuống dưới 30%.
4. **Chế độ tương phản cao:** Chuyển đổi nền đen sâu với các đường viền vàng/đỏ/xanh đậm nét, thanh đo tương phản cao, hỗ trợ người khiếm thị màu và môi trường ánh sáng mạnh.

---

## 4. Các lệnh kiểm thử, Benchmark & Soak

- **Kiểm thử tự động (95/95 test case PASS 100%):**
  ```bash
  PYTHONPATH=tests:. python3 -m unittest discover -s tests -v
  ```
- **Kiểm tra danh sách thành viên:**
  ```bash
  python3 tools/check_team.py
  ```
- **Benchmark có render (Contract v1.3):**
  ```bash
  python3 -m chonoi.bench --seed 42 --duration 30 --out bench.json
  ```
  *(Đo cảnh lặn sáng lõi tại 1280×720, làm nóng 3s, đo 30s. Kết quả: avg 60.0 FPS, 1% low 55.6 FPS, load 76 ms).*
- **Soak headless (10 Ngày liên tục không lỗi):**
  ```bash
  python3 -m chonoi.soak --seed 7 --days 10 --out soak.json
  ```
  *(Chạy 10 Ngày lặp chu kỳ D1–D5 bằng bot tất định. Kết quả: 10/10 Ngày completed, 0 crashes, thời gian < 1s).*

---

## 5. Bàn giao & Release v1.0.0

- **Git tag:** `phase-1`, `phase-3`, `phase-4`
- **GitHub Release:** `v1.0.0`
- **Tài liệu truy vết & Bằng chứng:**
  - Ma trận truy vết Phase 4: [`docs/verification/phase-4.md`](docs/verification/phase-4.md)
  - Ma trận truy vết Phase 3: [`docs/verification/phase-3.md`](docs/verification/phase-3.md)
  - Minh chứng hiệu năng: [`docs/proof/phase-4/bench.json`](docs/proof/phase-4/bench.json) và [`docs/proof/phase-4/soak.json`](docs/proof/phase-4/soak.json)
  - Nhật ký AI & Làm rõ: [`docs/ai-usage-log.md`](docs/ai-usage-log.md), [`docs/clarify.md`](docs/clarify.md)
  - Tổng kết & Phản tư: [`docs/retro.md`](docs/retro.md), [`docs/members/HieuVuong145.md`](docs/members/HieuVuong145.md), [`docs/members/ngdinhtruong28.md`](docs/members/ngdinhtruong28.md)
  - Lịch sử thay đổi: [`CHANGELOG.md`](CHANGELOG.md)
  - Bản quyền & Đóng góp: [`LICENSE`](LICENSE), [`CREDITS.md`](CREDITS.md)
