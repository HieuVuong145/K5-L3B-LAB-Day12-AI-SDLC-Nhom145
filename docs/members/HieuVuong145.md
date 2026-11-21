# HieuVuong145 — phản tư cá nhân (≤ 200 từ)

- Tôi đã làm (kèm link commit): Thiết lập kickoff nhóm, điều chỉnh quy mô nhóm 2 người trong `game.contract.json` và `tools/check_team.py`, phụ trách module `sim/gather` (hoàn thiện Lát 1 bơi/oxy/ngạt và Lát 2 hái nút/bắt cá), viết bộ unit test `tests/test_gather.py`.
- Tôi đã review (kèm link): Đọc và kiểm tra chéo module `sim/quan` do bạn Trường phụ trách, xác nhận luồng sự kiện từ bếp đến bàn và đóng ca đúng theo PRD-0 mục F.
- AI sai ở đâu và tôi phát hiện thế nào: AI từng xuất sự kiện `faint` với dữ liệu `pos` thay vì `{"cause": "choke", "lost": lost, "hp": 0}` theo PRD mục E; tôi đã đối chiếu kỹ bảng schema và sửa lại dữ liệu cho đúng chuẩn LIFO.
- Điều tôi học được: Cách phát triển theo hợp đồng (Contract-Driven Development), kiểm tra tính tất định của simulation và cách phối hợp nhịp nhàng khi dùng AI làm tăng tốc độ viết code và unit test.
