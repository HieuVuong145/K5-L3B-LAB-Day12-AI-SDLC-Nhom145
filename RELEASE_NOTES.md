# Release Notes — Quán Ăn Chợ Nổi v1.0.0

Phiên bản phát hành chính thức v1.0.0 của dự án Quán Ăn Chợ Nổi (Nhóm 145 — Vương Toàn Minh Hiếu & Nguyễn Đình Trường).

## Điểm mới nổi bật
1. **Gameplay hoàn chỉnh theo Test Contract v1.3:**
   - **Buổi sáng (`gather`):** Út Sen lặn bắt cá linh, cá lóc, cá kèo và hái bông điên điển, bông súng, kèo nèo. Quản lý bình oxy, thời gian ngạt, hồi máu và né tránh thủy quái Cá Sấu Năm Chèo.
   - **Buổi tối (`quan`):** Mở quán ăn trên nhà bè Má Tư, đón khách theo lịch, quản lý bếp nấu, phục vụ đúng bàn, nhận tiền boa và duy trì điểm uy tín.
   - **Chu kỳ Ngày (`day`):** Vòng lặp `gather -> quan -> shop` xuyên suốt với khả năng nâng cấp bình oxy và áo phao tại Tiệm Chú Sáu.
2. **Cơ chế độ tươi & Kho cá thể:**
   - Quản lý từng cá thể nguyên liệu `{id, kind, fresh}`.
   - Hao tươi theo thời gian thực (giỏ 0.5/s, kho 0.25/s), phát sự kiện `spoiled` khi xuống dưới ngưỡng 30.
   - Giá món `base_price` chốt tự động theo độ tươi trung bình của nguyên liệu nấu.
3. **Cảnh báo trực quan & Chế độ tương phản cao:**
   - 3 cảnh báo chữ + biểu tượng: `⚠️ CÁ SẤU ĐANG ĐẾN GẦN! 🐊`, `⚠️ OXY SẮP HẾT! 🫧`, `⚠️ KHÁCH SẮP GIẬN! 💢`.
   - Chế độ tương phản cao (High Contrast Mode) bật/tắt nhanh bằng phím `H` hoặc nút trên giao diện.
4. **Hiệu năng & Đo kiểm tự động:**
   - Công cụ Benchmark có render (`chonoi/bench.py`) đạt avg 60.0 FPS, 1% low 55.6 FPS, load 76 ms.
   - Công cụ Soak headless (`chonoi/soak.py`) chạy liên tục 10 Ngày không lỗi (crashes = 0).
   - Toàn bộ 95/95 bài kiểm thử unit test đạt màu xanh (100% PASS).

## Hướng dẫn chạy nhanh (≤ 3 lệnh)
```bash
git clone https://github.com/HieuVuong145/K5-L3B-LAB-Day12-AI-SDLC-Nhom145.git && cd K5-L3B-LAB-Day12-AI-SDLC-Nhom145
PYTHONPATH=tests:. python3 -m unittest discover -s tests -v
python3 -m chonoi.live --mode gather
```

## Giới hạn đã biết (Known Limitations)
- Game được thiết kế cho trải nghiệm một người chơi cục bộ (local single player) trên nền web canvas chuẩn.
- Các thiết bị có GPU quá cũ có thể bật Chế độ tương phản cao để tối ưu tốc độ vẽ khung hình.
