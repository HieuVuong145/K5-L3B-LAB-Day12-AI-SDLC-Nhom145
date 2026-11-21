# Hợp đồng tích hợp (Hợp đồng Lặn & Hái → Mở Quán)

Thống nhất giữa các module trong nhóm Nhom145 theo PRD-0:

### 1. Schema file kho (`inventory.json`)
File chỉ chứa khóa `items`, object ánh xạ `kind` → số nguyên dương (loại bỏ khóa có lượng 0). Kho rỗng biểu diễn là `{"items": {}}`.
- File mẫu hợp lệ: [`inventory.sample.json`](inventory.sample.json)
- Khi `gather_end`: file kho được ghi nguyên tử (atomic write qua file tạm) đúng một lần. Nếu ngất (`fainted`), xuất kho rỗng.
- Chế độ `quan`: đọc file kho nạp vào `stock`.

Ví dụ:
```json
{"items": {"bong_sung": 2, "ca_loc": 1}}
```

### 2. Giao diện giữa `sim/*` và `client/ui`
- **UI đọc trạng thái:** Qua phương thức `sim.snapshot()` trả về dictionary chứa:
  - Chung: `player`, `mode`, `time_left_ticks`, `money`, `earned`, `reputation`, `score`.
  - Gather: `hold`, `hold_count`, `hold_capacity`, `nodes[]`, `fish[]`, `at_surface`.
  - Quan: `stock`, `hand`, `stoves[]`, `tables[]`, `customers[]`.
- **UI gửi lệnh vào sim:** Qua `InputState` gồm:
  - `move: [x, d]` (gather) hoặc `move: [x, z]` (quan), biên độ trong $[-1, 1]$.
  - `interact: bool`: phím E (cạnh lên từ false sang true) dùng để hái/cập bến (gather) hoặc nấu/nhấc/phục vụ (quan).
  - `catch: bool`: phím Space (cạnh lên) dùng để bắt cá khi lặn (gather).

### 3. Danh sách sự kiện (Events)
- **Gather:**
  - `dive`, `surface`: `pos` sau di chuyển khi đổi phía biên mặt nước $d = 0.5\,\text{m}$.
  - `oxygen_empty`: `{"oxygen_ticks": 0}` khi vừa chạm 0.
  - `choke`: `{"hp": hp}` khi đủ 60 tick ngạt.
  - `faint`: `{"cause": "choke", "lost": [...], "hp": 0}` khi máu về 0 (lost theo thứ tự LIFO).
  - `gather`: `{"node_id": ..., "kind": ..., "amount": 1}` khi hái thành công.
  - `fish_caught`: `{"fish_id": ..., "kind": ..., "yield": ...}` khi bắt thành công đàn cá.
  - `hold_full`: `{"action": "gather"|"catch", ..., "required": ..., "free": ...}` khi giỏ thiếu chỗ.
  - `node_regrown`: `{"node_id": ...}` khi nút cây mọc lại.
  - `gather_end`: `{"reason": "docked"|"time"|"fainted", "inventory": {...}}`.
- **Quan:**
  - `customer_arrived`: `{"order_id": ..., "table_id": ..., "dish_id": ...}` khi khách vào bàn.
  - `no_dish`: `{}` khi có bàn trống nhưng kho không đủ nấu bất kỳ món nào.
  - `cook_started`: `{"stove_id": ..., "order_id": ..., "dish_id": ..., "items": [...], "base_price": ...}` khi bắt đầu nấu.
  - `dish_ready`: `{"stove_id": ..., "order_id": ..., "dish_id": ...}` khi bếp nấu xong.
  - `dish_picked`: `{"stove_id": ..., "order_id": ..., "dish_id": ...}` khi người chơi nhấc món.
  - `served`: `{"order_id": ..., "table_id": ..., "dish_id": ..., "patience_ticks_left": ..., "base_price": ..., "tip": ...}` khi phục vụ bàn.
  - `paid`: `{"order_id": ..., "table_id": ..., "base_price": ..., "tip": ..., "amount": ..., "reason": "finished_eating"|"closing"}`.
  - `customer_left`: `{"order_id": ..., "table_id": ..., "reason": "patience"|"closing", "reputation": ...}`.
  - `quan_end`: `{"reason": "time", "money": ..., "earned": ..., "shift_earned": ..., "reputation": ...}`.
