# Changelog

Tất cả thay đổi đáng chú ý của dự án Quán Ăn Chợ Nổi (Nhom145) sẽ được ghi lại trong file này.

## [v1.2.0] - Phase 3 (Change Request "Mùa Nước Nổi") - 2026-11-21

### ⚠️ BREAKING CHANGES
1. **Chuyển đổi schema kho từ kho đếm sang kho cá thể (Individual Items Schema):**
   - Định dạng cũ (v1.0/v1.1): `{"items": {"ca_loc": 2, "bong_sung": 1}}`
   - Định dạng mới (v1.2): `{"items": [{"id": "I1", "kind": "ca_linh", "fresh": 100.0}, {"id": "I2", "kind": "ca_loc", "fresh": 97.5}]}`
   - File có duy nhất khóa gốc `items` chứa danh sách cá thể `{id, kind, fresh}`. Kho rỗng là `{"items": []}`.
   - Khi chạy ở `contract_version: "1.2"`, file kho đếm cũ hoặc sai schema sẽ bị từ chối với mã thoát `2` (`BadInput`).
   - Cập nhật fixture: Các scenario chứa `gather.hold` hoặc `quan.stock` cần dùng mảng cá thể `[{"id": ..., "kind": ..., "fresh": ...}]`.

2. **Cơ chế giữ chỗ theo ID thay vì theo số lượng (`reserved`):**
   - Trường `customers[].reserved` trong Quán chuyển từ object đếm thành mảng ID cá thể (ví dụ: `["I1", "I3"]`).
   - Món gọi tự động giữ các cá thể khả dụng tươi nhất (`fresh >= 30`), hòa theo ID nhỏ hơn.
   - Khi một cá thể trong phần giữ bị ươn (`fresh < 30`), sim tự động nhả phần giữ và thử giữ lại đúng một lần từ kho còn lại. Nếu không đủ, đơn chuyển thành `unfulfillable` và khách đợi hết kiên nhẫn.

3. **Giá món theo độ tươi (`freshness-adjusted base price`):**
   - Khi bếp bắt đầu nấu (`cook_started`), tiêu đúng các ID cá thể đang giữ và chốt:
     `base_price = floor(giá niêm yết × avg_fresh / 100)`
   - Tiền boa (nếu đủ điều kiện) tính theo `floor(base_price × 0.2)`.

### Added
- **Cơ chế hao tươi (Freshness Decay) & Ngưỡng ươn 30:**
  - Hàng mới bắt/hái bắt đầu ở `fresh = 100.0`, hao tươi từ bước sau.
  - Tốc độ hao: giỏ gather giảm `0.5/s` (`0.5/60` mỗi tick); kho quán giảm `0.25/s` (`0.25/60` mỗi tick) kể cả hàng đang giữ chỗ.
  - Sự kiện `spoiled`: phát đúng một lần khi độ tươi giảm từ $\ge 30$ xuống $< 30$ mang `{item_id, kind, location: "hold" | "stock"}`. Sắp xếp theo ID khi nhiều cá thể cùng ươn.
  - Hàng ươn (`fresh < 30`) vẫn chiếm ô trong kho nhưng không được dùng để nấu.
- **HUD hiển thị độ tươi:**
  - HUD giỏ buổi sáng và kho buổi tối hiển thị tỷ lệ tươi trung bình `%` và cảnh báo hàng ươn `⚠️`.
- **Bộ test hồi quy & độ tươi Phase 3 (`tests/test_freshness.py`):**
  - Kiểm tra ngưỡng biên 30, phát `spoiled` một lần, sắp xếp ID, bàn giao kho cá thể giữa gather và quan, tính giá theo fresh, giữ lại khi hàng ươn.

### Changed / Regression Updates
- `test_smoke_p1.py`:
  - `test_time_ends_gather_and_keeps_hold`: Cập nhật kiểm tra cấu trúc mảng cá thể `items` thay vì object đếm.
  - `test_inv_01_gather_writes_inventory_quan_reads_it`: Cập nhật bàn giao mảng cá thể 3 nguyên liệu, so khớp snapshot kho quán với file kho sau hao tươi.
  - `test_inv_bad_schema_exit_2`: Thêm kiểm tra từ chối kho đếm v1.0 trả mã 2 theo Contract v1.2.
  - `test_inventory_and_scenario_stock_conflict`: Cập nhật scenario kho sang mảng cá thể.
- `test_gather.py`:
  - `test_gather_node_success`, `test_catch_fish_success`: So sánh loại nguyên liệu của cá thể trong `sim.hold`.
  - `test_faint_clears_hold_lifo`: Kiểm tra danh sách cá thể bị rơi theo thứ tự LIFO và `inventory_items()` trả về mảng rỗng.
- `test_quan.py`:
  - `test_full_cooking_serving_and_payment_flow`: Cập nhật `base_price` mong đợi từ `60` thành `59` do cá thể lóc nướng trui bị hao tươi 1 tick trước khi nấu (`floor(60 * 99.996 / 100) = 59`), tiền boa `floor(59 * 0.2) = 11`, tổng trả `70`.

## [v1.0.0] - Phase 1 - 2026-11-21
- Hoàn thành Phase 1 theo PRD-0 và Test Contract v1.0.
- Lát 1: Bơi, lặn, nổi, oxy, ngạt, ngất LIFO.
- Lát 2: Hái nút, bắt cá, cập bến, xuất kho.
- Lát 3: Khách theo lịch, chọn món, giữ chỗ, kiên nhẫn.
- Lát 4: Nấu tại bếp B1, nhấc món, bưng phục vụ bàn T1, tính tiền, boa, đóng ca.
