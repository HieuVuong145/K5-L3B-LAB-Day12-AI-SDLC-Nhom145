# Hợp đồng tích hợp (Hợp đồng Lặn & Hái → Mở Quán — Contract v1.2)

Thống nhất giữa các module trong nhóm Nhom145 theo PRD-0 và TICKET-03 (Phase 3):

### 1. Schema file kho (`inventory.json`) — Kho cá thể (v1.2)
- [THAY THẾ] Thay thế kho đếm v1.0 bằng kho cá thể v1.2. File có đúng khóa gốc `items`, giá trị là mảng cá thể `{"id": str, "kind": str, "fresh": float}`.
- Kho rỗng biểu diễn là `{"items": []}`.
- `id`: chuỗi duy nhất, không rỗng, cấp tuần tự `I1`, `I2`, ...
- `kind`: thuộc danh mục nguyên liệu (`ca_loc`, `ca_linh`, `ca_keo`, `bong_dien_dien`, `bong_sung`, `keo_neo`).
- `fresh`: số thực hữu hạn trong đoạn $[0, 100]$.
- Contract v1.2 từ chối kho đếm hoặc sai schema, kind lạ, id trùng, fresh ngoài miền bằng mã thoát 2.
- File mẫu hợp lệ: [`inventory.sample.json`](inventory.sample.json).
- Khi `gather_end`: file kho được ghi nguyên tử (atomic write qua file tạm cùng thư mục) đúng một lần. Nếu ngất (`fainted`), xuất kho rỗng `{"items": []}`.
- Chế độ `quan`: đọc file kho nạp nguyên vẹn vào `stock` (kể cả hàng ươn).

Ví dụ:
```json
{
  "items": [
    {"id": "I1", "kind": "ca_linh", "fresh": 100.0},
    {"id": "I2", "kind": "ca_loc", "fresh": 97.5},
    {"id": "I3", "kind": "bong_sung", "fresh": 85.0}
  ]
}
```

### 2. Giao diện giữa `sim/*` và `client/ui`
- **UI đọc trạng thái:** Qua phương thức `sim.snapshot()` trả về dictionary chứa:
  - Chung: `player`, `mode`, `time_left_ticks`, `money`, `earned`, `reputation`, `score`.
  - Gather: `hold` (mảng cá thể `{id, kind, fresh}`), `hold_count`, `hold_capacity`, `nodes[]`, `fish[]`, `at_surface`.
  - Quan: `stock` (mảng cá thể `{id, kind, fresh}`), `hand`, `stoves[]`, `tables[]`, `customers[]` (mỗi khách có `reserved` là mảng id cá thể).
- **UI gửi lệnh vào sim:** Qua `InputState` gồm:
  - `move: [x, d]` (gather) hoặc `move: [x, z]` (quan), biên độ trong $[-1, 1]$.
  - `interact: bool`: phím E (cạnh lên) dùng để hái/cập bến (gather) hoặc nấu/nhấc/phục vụ (quan).
  - `catch: bool`: phím Space (cạnh lên) dùng để bắt cá khi lặn (gather).

### 3. Danh sách sự kiện (Events)
- **Gather:**
  - `dive`, `surface`: `pos` sau di chuyển khi đổi phía biên mặt nước $d = 0.5\,\text{m}$.
  - `oxygen_empty`: `{"oxygen_ticks": 0}` khi vừa chạm 0.
  - `choke`: `{"hp": hp}` khi đủ 60 tick ngạt.
  - `faint`: `{"cause": "choke", "lost": [...], "hp": 0}` khi máu về 0 (`lost` là mảng cá thể theo thứ tự bỏ LIFO).
  - `gather`: `{"node_id": ..., "kind": ..., "amount": 1}` khi hái thành công.
  - `fish_caught`: `{"fish_id": ..., "kind": ..., "yield": ...}` khi bắt thành công đàn cá.
  - `hold_full`: `{"action": "gather"|"catch", ..., "required": ..., "free": ...}` khi giỏ thiếu chỗ.
  - `node_regrown`: `{"node_id": ...}` khi nút cây mọc lại.
  - `spoiled`: `{"item_id": ..., "kind": ..., "location": "hold"}` khi độ tươi giảm từ $\ge 30$ xuống $< 30$.
  - `gather_end`: `{"reason": "docked"|"time"|"fainted", "inventory": {"items": [...]}}`.
- **Quan:**
  - `customer_arrived`: `{"order_id": ..., "table_id": ..., "dish_id": ...}` khi khách vào bàn.
  - `no_dish`: `{}` khi có bàn trống nhưng kho không đủ nấu bất kỳ món nào.
  - `spoiled`: `{"item_id": ..., "kind": ..., "location": "stock"}` khi độ tươi trong kho giảm từ $\ge 30$ xuống $< 30$.
  - `cook_started`: `{"stove_id": ..., "order_id": ..., "dish_id": ..., "table_id": ..., "items": [...], "base_price": ...}` khi bắt đầu nấu (`items` sắp theo kind rồi id; `base_price = floor(listed_price * avg_fresh / 100)`).
  - `dish_ready`: `{"stove_id": ..., "order_id": ..., "dish_id": ...}` khi bếp nấu xong.
  - `dish_picked`: `{"stove_id": ..., "order_id": ..., "dish_id": ...}` khi người chơi nhấc món.
  - `served`: `{"order_id": ..., "table_id": ..., "dish_id": ..., "patience_ticks_left": ..., "base_price": ..., "tip": ...}` khi phục vụ bàn.
  - `paid`: `{"order_id": ..., "table_id": ..., "base_price": ..., "tip": ..., "amount": ..., "reason": "finished_eating"|"closing"}`.
  - `customer_left`: `{"order_id": ..., "table_id": ..., "reason": "patience"|"closing", "reputation": ...}`.
  - `quan_end`: `{"reason": "time", "money": ..., "earned": ..., "shift_earned": ..., "reputation": ..., "served": ..., "left": ..., "tips": ...}`.
