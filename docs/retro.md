# Retro nhóm

## Phase 2 (nhanh)
- Điều tốt: Đã nối được hai tiến trình và cấu hình chuẩn theo PRD.
- Điều tệ: Khi merge branch giữa hai thành viên dễ dẫn đến lệch tên trường sự kiện nếu không đối chiếu hợp đồng.
- 1 hành động cho Phase 3: Thống nhất chặt chẽ schema kho và event payload trong `docs/contracts/` trước khi sửa sim.

## Phase 3 (Đổi kho cá thể & Độ tươi)
- Điều tốt: Đổi schema kho từ kho đếm sang kho cá thể `{id, kind, fresh}` nhanh gọn, viết test migration và unit test bao quát đầy đủ ngưỡng biên.
- Điều tệ: Làm tròn float giữa file JSON và JSONL cần sự đồng nhất (`_clean` round 3 chữ số) để tránh lệch phần nghìn khi so sánh snapshot.
- Điều rút ra từ lần đổi kho:
  1. Khi có Breaking Change về schema dữ liệu, cập nhật hợp đồng và schema validator trước tiên để phát hiện lỗi từ sớm.
  2. Bổ sung ngay các test từ chối schema cũ (mã 2) và test bàn giao file để đảm bảo tính tương thích giữa các module.
  3. Cơ chế decay ở đầu tick giúp hàng mới sinh tự động không bị hao ở tick hiện tại mà chỉ hao từ tick kế tiếp mà không cần cờ phụ phức tạp.

## Phase 4 (cuối — Phát hành v1.0.0)
- **Rà lại hành động Phase 2:**
  - *Hành động đã chốt ở P2:* Thống nhất chặt chẽ schema kho và event payload trong `docs/contracts/` trước khi sửa code simulation.
  - *Đánh giá:* Nhóm đã thực hiện triệt để ở Phase 3 và Phase 4. Nhờ cập nhật hợp đồng và kiểm tra schema ngay từ đầu, quá trình nâng cấp kho cá thể và thêm benchmark/soak diễn ra trơn tru mà không làm hỏng nhánh chính hay vỡ các test cũ.
- **Điều làm tốt:**
  - Viết công cụ benchmark và soak chạy hoàn toàn tự động, đạt chuẩn hiệu năng cao (avg 60 FPS, p1 low 55.6 FPS, load 76ms; soak 10 ngày hoàn tất trong 0.7s với 0 lỗi).
  - Cải tiến giao diện người dùng trực quan với 3 cảnh báo bằng chữ và biểu tượng (Cá Sấu, Oxy, Khách sắp giận) và chế độ tương phản cao hoạt động ổn định.
  - Toàn bộ 95 test case đều xanh (100% OK).
- **Điều cần cải thiện:**
  - Chú ý xử lý các sai số nhỏ của đồng hồ trình duyệt (timer jitter) khi đo benchmark để tránh bị fail assertion biên (59.99 FPS vs 60 FPS).
- **Số liệu nhóm:**
  - Số commit phân bổ đều giữa cả 2 thành viên trên repo chung.
  - Mỗi commit đều có kiểm thử hồi quy trước khi đẩy.
- **Một lần AI sai và cách nhóm phát hiện:**
  - Trong lệnh soak ban đầu, AI đã gọi `InputState()` rỗng thay vì dùng `LiveInputs()`, dẫn đến lỗi thiếu tham số `move`, `held`, `edges`. Nhóm đã phát hiện ngay khi chạy smoke test soak và sửa lại bằng cách tái sử dụng `LiveInputs` có sẵn trong khung mã nguồn.
- **Nếu làm lại, đổi gì:**
  - Tự động hóa việc tạo artifact proof bằng hook pre-commit để tiết kiệm thời gian chạy thủ công ở các phút cuối.
