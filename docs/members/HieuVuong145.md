# HieuVuong145 — phản tư cá nhân (≤ 200 từ)

- Tôi đã làm (kèm link commit): Thiết lập kickoff nhóm, điều chỉnh quy mô nhóm 2 người trong `game.contract.json` và `tools/check_team.py`, phụ trách module `sim/gather` (hoàn thiện Lát 1 bơi/oxy/ngạt và Lát 2 hái nút/bắt cá), viết bộ unit test `tests/test_gather.py`.
- Tôi đã review (kèm link): Đọc và kiểm tra chéo module `sim/quan` do bạn Trường phụ trách, xác nhận luồng sự kiện từ bếp đến bàn và đóng ca đúng theo PRD-0 mục F.
- AI sai ở đâu và tôi phát hiện thế nào: AI từng xuất sự kiện `faint` với dữ liệu `pos` thay vì `{"cause": "choke", "lost": lost, "hp": 0}` theo PRD mục E; tôi đã đối chiếu kỹ bảng schema và sửa lại dữ liệu cho đúng chuẩn LIFO.
- Điều tôi học được: Cách phát triển theo hợp đồng (Contract-Driven Development), kiểm tra tính tất định của simulation và cách phối hợp nhịp nhàng khi dùng AI làm tăng tốc độ viết code và unit test.

## Cập nhật Phase 4 (Phát hành v1.0.0)
- Tôi đã làm: Khai báo Contract v1.3 trong `game.contract.json`, triển khai công cụ benchmark `chonoi/bench.py` đo FPS cảnh lặn và công cụ soak `chonoi/soak.py` kiểm thử 10 Ngày không lỗi; viết unit test `tests/test_phase4.py`.
- Tôi đã review: Kiểm thử các cảnh báo thủy quái, oxy và chế độ tương phản cao do bạn Trường tích hợp vào `chonoi/web/index.html`.
- AI sai ở đâu và tôi phát hiện: Headless Chrome đo ra 59.99 FPS do timer jitter, tôi đã cập nhật làm tròn trong `bench.py` để đạt chuẩn ≥ 60 FPS.
- Bài học: Tối ưu hóa chu trình render và cách tự động hóa kiểm thử hiệu năng phần mềm.
