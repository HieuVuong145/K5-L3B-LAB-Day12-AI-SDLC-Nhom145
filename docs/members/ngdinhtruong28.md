# ngdinhtruong28 — phản tư cá nhân (≤ 200 từ)

- Tôi đã làm (kèm link commit): Phụ trách module `sim/quan` (hoàn thiện Lát 3 khách đến/giữ chỗ và Lát 4 nấu/phục vụ/tính tiền), xây dựng bộ unit test `tests/test_quan.py` kiểm thử toàn bộ luồng vòng đời của Quán.
- Tôi đã review (kèm link): Review chéo module `sim/gather` của bạn Hiếu, kiểm tra khả năng xuất file kho nguyên tử và kiểm thử tích hợp 2 tiến trình headless (gather xuất kho -> quan nạp kho).
- AI sai ở đâu và tôi phát hiện thế nào: Khi viết test phục vụ món, AI giữ nguyên `interact=True` liên tục giữa lúc bưng món và phục vụ dẫn đến sim không phát hiện cạnh lên (rising edge). Nhờ đọc kỹ `chonoi/inputs.py`, tôi đã chèn `interact=False` để test kích hoạt đúng cạnh lên.
- Điều tôi học được: Hiểu rõ cơ chế xử lý đầu vào theo cạnh lên (edge-triggered) trong game simulation, tầm quan trọng của việc kiểm thử tự động hộp đen và cách kiểm soát uy tín/tiền nong trong ca phục vụ.
