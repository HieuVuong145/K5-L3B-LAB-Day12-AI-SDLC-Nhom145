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

## Phase 4 (cuối)
- Rà lại hành động Phase 2: đã làm chưa? vì sao?
- Điều tốt / điều tệ:
- Số liệu: số commit theo người, cách đọc code của nhau, token theo người:
- Một lần AI sai và cách nhóm phát hiện:
- Nếu làm lại, đổi gì:
