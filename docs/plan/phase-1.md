# Kế hoạch Phase 1 (PRD-0 — Quán Ăn Chợ Nổi)

## Mục tiêu
- Xây dựng hoàn thiện luật chơi lõi Phase 1 theo Test Contract v1.0.
- Hoàn thành 4 lát cắt (slices) song song:
  - Lát 1: Bơi, oxy, ngạt, Máu, chặn biên, giỏ LIFO.
  - Lát 2: Hái nút mặt nước, bắt cá khi lặn, cập bến bến đò, xuất file kho.
  - Lát 3: Quán mở ca, khách đến theo lịch, chọn món khả dụng, chiếm giữ nguyên liệu, kiên nhẫn.
  - Lát 4: Bếp B1 nấu, nhấc món lên tay, phục vụ bàn T1, thanh toán, boa, uy tín, đóng ca.
- Đảm bảo tính tất định (cùng seed -> output byte-for-byte), toàn bộ test xanh 100%, nộp tag `phase-1` trước 1:00.

## Phân công việc / Người / Phụ thuộc
- **Vương Toàn Minh Hiếu (@HieuVuong145):** Phụ trách module `sim/gather` (Lát 1, Lát 2), vai PO & Integrator.
- **Nguyễn Đình Trường (@ngdinhtruong28):** Phụ trách module `sim/quan` (Lát 3, Lát 4) và `qa` test suite, vai QA Lead & Scrum.
- Phụ thuộc: Quán phụ thuộc vào schema file kho xuất từ Gather (thống nhất ở `docs/contracts/README.md`).

## Rủi ro & Giải pháp
1. *Rủi ro lệch hợp đồng sự kiện/kho giữa hai chế độ:* Chốt sớm schema kho `{"items": {<kind>: <int>}}` và danh sách event tại `docs/contracts/README.md`.
2. *Rủi ro quy mô nhóm:* Nhóm 2 người được chấp thuận theo `docs/clarify.md`, điều chỉnh test thành viên `check_team.py` cho phép 2–6 thành viên.
3. *Rủi ro thời gian gấp (60 phút):* Tập trung 100% vào luật lõi và test tự động, không thêm cơ chế phức tạp ngoài hợp đồng ở Phase 1.
