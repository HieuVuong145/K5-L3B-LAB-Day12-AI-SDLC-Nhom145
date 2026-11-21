# ngdinhtruong28 — phản tư cá nhân (≤ 200 từ)

- Tôi đã làm (kèm link commit): Phụ trách module `sim/quan` (hoàn thiện Lát 3 khách đến/giữ chỗ và Lát 4 nấu/phục vụ/tính tiền), xây dựng bộ unit test `tests/test_quan.py` kiểm thử toàn bộ luồng vòng đời của Quán.
- Tôi đã review (kèm link): Review chéo module `sim/gather` của bạn Hiếu, kiểm tra khả năng xuất file kho nguyên tử và kiểm thử tích hợp 2 tiến trình headless (gather xuất kho -> quan nạp kho).
- AI sai ở đâu và tôi phát hiện thế nào: Khi viết test phục vụ món, AI giữ nguyên `interact=True` liên tục giữa lúc bưng món và phục vụ dẫn đến sim không phát hiện cạnh lên (rising edge). Nhờ đọc kỹ `chonoi/inputs.py`, tôi đã chèn `interact=False` để test kích hoạt đúng cạnh lên.
- Điều tôi học được: Hiểu rõ cơ chế xử lý đầu vào theo cạnh lên (edge-triggered) trong game simulation, tầm quan trọng của việc kiểm thử tự động hộp đen và cách kiểm soát uy tín/tiền nong trong ca phục vụ.

## Cập nhật Phase 3
- Tôi đã làm: Nâng cấp Quán cho Contract v1.2: cơ chế hao tươi kho thô 0.25/s, phát `spoiled` theo ID, cơ chế giữ chỗ theo ID cá thể và re-reserve khi nguyên liệu giữ bị ươn, tính giá chốt `base_price` và cập nhật HUD trực tiếp hiển thị độ tươi và cảnh báo ươn.
- Tôi đã review: Review module Gather và adapter kho cá thể của bạn Hiếu; chạy kiểm thử toàn bộ test suite và đối chiếu khớp output JSONL.
- AI sai ở đâu và tôi phát hiện thế nào: Trong test nấu món, AI so sánh `base_price` với 60 nhưng thực tế sau 1 tick decay độ tươi giảm nhẹ khiến `floor(60 * 99.996 / 100) = 59`. Tôi đã phát hiện và cập nhật assertion cho đúng luật Phase 3.
- Điều tôi học được: Quản lý trạng thái phức tạp (state transitions) giữa các thực thể phụ thuộc nhau khi điều kiện biên (độ tươi < 30) kích hoạt.
