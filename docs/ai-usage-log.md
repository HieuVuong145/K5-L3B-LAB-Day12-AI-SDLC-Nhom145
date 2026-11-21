# Nhật ký dùng AI (theo phase và theo người)

| Phase | Người | Công cụ / model | Việc | Token / chi phí ước tính | Ghi chú (AI sai ở đâu?) |
|---|---|---|---|---|---|
| Phase 1 | Vương Toàn Minh Hiếu | Antigravity / Gemini 3.8 Flash | Làm rõ lỗi zsh nhận diện dấu `#` trong lệnh unittest; cập nhật TEAM.md và kiểm tra quy mô nhóm 2 người | ~15k tokens | zsh trên macOS mặc định tắt interactive comments khiến `#` bị parse thành start_dir |
| Phase 1 | Vương Toàn Minh Hiếu | Antigravity / Gemini 3.8 Flash | Hướng dẫn và triển khai Lát 2 (Hái, Bắt cá, Cập bến, Giỏ LIFO) trong `gather.py`; viết 10 unit test | ~25k tokens | Ban đầu event faint trả về `pos` thay vì `{"cause": "choke", "lost": lost, "hp": 0}` theo PRD mục E |
| Phase 1 | Nguyễn Đình Trường | Antigravity / Gemini 3.8 Flash | Triển khai Lát 4 (Bếp nấu, Bưng bê, Phục vụ, Boa, Uy tín, Đóng ca) trong `quan.py`; viết 5 unit test | ~30k tokens | Nhầm lẫn giữa giữ phím và cạnh lên (rising edge) của `interact`, đã sửa test để tạo cạnh lên |
