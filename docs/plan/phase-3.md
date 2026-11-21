# Kế hoạch Phase 3 (TICKET-03 — Change Request "Mùa Nước Nổi")

## 1. Mục tiêu
- Nâng cấp hệ thống lên Test Contract v1.2 (`contract_version: "1.2"`).
- Triển khai Breaking Change: chuyển từ kho đếm theo loại sang kho cá thể (Individual Items Schema) `{"items": [{"id": ..., "kind": ..., "fresh": ...}]}`.
- Cơ chế độ tươi (Freshness):
  - Hàng mới sinh bắt đầu với `fresh = 100.0`, hao tươi từ bước sau.
  - Tốc độ hao: giỏ gather `-0.5/s` (`-0.5/60` mỗi tick); kho quán `-0.25/s` (`-0.25/60` mỗi tick).
  - Ngưỡng ươn: `fresh < 30.0` phát sự kiện `spoiled` một lần duy nhất, không dùng nấu ăn nhưng vẫn chiếm ô.
  - Giữ chỗ theo ID: giữ cá thể khả dụng tươi nhất (`fresh >= 30`), nếu cá thể giữ bị ươn thì nhả và thử giữ lại một lần.
  - Giá theo tươi: `base_price = floor(giá niêm yết × avg_fresh / 100)`, tính boa trên `base_price` đã chốt.
- Bàn giao kho cá thể giữa Gather và Quán thông qua file kho và qua snapshot.
- Bổ sung HUD độ tươi / cảnh báo ươn trên giao diện trực tiếp (`chonoi/web/index.html`).
- Chạy 100% test xanh (bao gồm regression P1-P2 và test mới P3), đẩy tag `phase-3` trước 2:30.

---

## 2. Bảng phân tích tác động (Impact Analysis)

| Module | File cần đổi | Test bị ảnh hưởng | Người phụ trách |
| :--- | :--- | :--- | :--- |
| **Contract & Config** | `game.contract.json`, `chonoi/contract.py` | `test_contract_v12_*`, `test_smoke_p1.py` | @HieuVuong145 |
| **Inventory Adapter** | `chonoi/inventory.py` | `test_inv_bad_schema_exit_2`, `test_inv_01_*` | @HieuVuong145 |
| **Scenario** | `chonoi/scenario.py` | `test_scenario_out_of_domain_exit_2`, `test_inventory_and_scenario_stock_conflict` | @HieuVuong145 |
| **Lặn (Gather)** | `chonoi/sim/gather.py` | `test_gather_exact_threshold_30_emits_spoiled`, `test_gather_node_success`, `test_catch_fish_success`, `test_faint_clears_hold_lifo` | @HieuVuong145 |
| **Quán (Quan)** | `chonoi/sim/quan.py` | `test_customer_arrives_and_reserves_stock`, `test_full_cooking_serving_and_payment_flow`, `test_price_calculation_with_freshness_and_tip` | @ngdinhtruong28 |
| **HUD & Web** | `chonoi/web/index.html` | Kiểm tra trực quan trên live server | @ngdinhtruong28 |
| **QA & Verification**| `tests/test_freshness.py`, `docs/verification/phase-3.md` | Bộ test `test_freshness.py` (11 test mới) | Cả hai (@HieuVuong145, @ngdinhtruong28) |

---

## 3. Quyết định kỹ thuật & Thứ tự tích hợp
1. **Quyết định schema kho cá thể:**
   - File kho chỉ có khóa gốc `items` là mảng các object `{id, kind, fresh}`.
   - Khi ở `contract_version: "1.2"`, từ chối file kho đếm dạng dict `{kind: count}` bằng mã 2 (`BadInput`).
   - Lưu trữ float được làm tròn 3 chữ số thập phân (`round(v, 3)`) qua hàm `_clean` để đồng nhất byte giữa file kho JSON và dòng sự kiện JSONL.
2. **Thứ tự tích hợp giữ main luôn chạy:**
   - Bước 1: Nâng cấp `game.contract.json` lên v1.2, bổ sung `freshness` tuning và validator trong `chonoi/contract.py`.
   - Bước 2: Cập nhật adapter `chonoi/inventory.py` và parser `chonoi/scenario.py` hỗ trợ kho cá thể và kiểm tra hợp lệ nghiêm ngặt.
   - Bước 3: Cập nhật `chonoi/sim/gather.py` (cấp ID cá thể, cơ chế hao tươi ở đầu tick, phát `spoiled`, LIFO faint, xuất kho).
   - Bước 4: Cập nhật `chonoi/sim/quan.py` (nạp kho cá thể, hao tươi, re-reserve khi ươn, tính `base_price` theo `avg_fresh`, trả `reason` và `amount` trong `paid`).
   - Bước 5: Cập nhật HUD trong `chonoi/web/index.html` hiển thị độ tươi và cảnh báo hàng ươn.
   - Bước 6: Cập nhật hồi quy cho `tests/test_smoke_p1.py`, `tests/test_gather.py`, `tests/test_quan.py` và viết mới `tests/test_freshness.py`.
   - Bước 7: Xuất dữ liệu chứng minh (`docs/proof/phase-3/`), cập nhật tài liệu và gắn tag `phase-3`.
