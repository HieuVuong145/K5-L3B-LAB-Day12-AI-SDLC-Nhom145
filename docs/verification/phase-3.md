# Ma trận truy vết Phase 3 (TICKET-03 — Change Request "Mùa Nước Nổi")

| AC | Nội dung yêu cầu | Cách kiểm chứng | Bằng chứng (link `docs/proof/phase-3/...`) | Kết quả |
| :--- | :--- | :--- | :--- | :--- |
| **AC-P3-01** | Test Contract v1.2 & cấu hình `freshness` chuẩn | Đọc `game.contract.json` & unit test `test_contract_v12_*` | [test_suite.txt](test_suite.txt) | **Đạt** |
| **AC-P3-02** | Kho cá thể `{id, kind, fresh}`, từ chối kho đếm trả mã 2 | Unit test `test_contract_v12_rejects_count_inventory`, `test_contract_v12_accepts_individual_inventory` | [test_suite.txt](test_suite.txt) | **Đạt** |
| **AC-P3-03** | Hao tươi Gather `-0.5/s`, ngưỡng 30 phát `spoiled` 1 lần | Chạy headless với scenario fresh:30 và unit test `test_gather_exact_threshold_30_emits_spoiled` | [threshold_sample.jsonl](threshold_sample.jsonl), [test_suite.txt](test_suite.txt) | **Đạt** |
| **AC-P3-04** | Bàn giao kho cá thể giữa 2 tiến trình Gather và Quán | Headless gather xuất kho lúc cập bến -> Headless quan đọc kho tại tick 0 so khớp chính xác | [inventory_sample.json](inventory_sample.json), [gather_sample.jsonl](gather_sample.jsonl), [quan_sample.jsonl](quan_sample.jsonl) | **Đạt** |
| **AC-P3-05** | Hao tươi Quán `-0.25/s`, phát `spoiled` theo thứ tự ID | Unit test `test_quan_stock_decay_and_spoiled` | [test_suite.txt](test_suite.txt) | **Đạt** |
| **AC-P3-06** | Giữ chỗ theo ID, nhả và thử giữ lại khi hàng giữ ươn | Unit test `test_reservation_re_reserve_when_item_spoils`, `test_reservation_fails_re_reserve_becomes_unfulfillable` | [test_suite.txt](test_suite.txt) | **Đạt** |
| **AC-P3-07** | Giá chốt theo fresh `floor(price * avg_fresh / 100)` & boa | Unit test `test_price_calculation_with_freshness_and_tip`, `test_full_cooking_serving_and_payment_flow` | [test_suite.txt](test_suite.txt) | **Đạt** |
| **AC-P3-08** | Hàng ươn (`fresh < 30`) không được dùng để nấu ăn | Unit test `test_spoiled_items_cannot_be_used_for_cooking` | [test_suite.txt](test_suite.txt) | **Đạt** |
| **AC-P3-09** | HUD hiển thị độ tươi và biểu tượng hàng ươn | Cập nhật `chonoi/web/index.html` với nhãn `%` và cảnh báo ươn | [index.html](../../chonoi/web/index.html) | **Đạt** |
| **AC-P3-10** | Hồi quy toàn bộ test suite P1-P2 và test mới P3 | Chạy `python3 -m unittest` toàn bộ 59 tests | [test_suite.txt](test_suite.txt) | **Đạt** (59/59) |
| **AC-P3-11** | Kiểm tra danh sách thành viên `TEAM.md` | Chạy `python3 tools/check_team.py` | [team_check.txt](team_check.txt) | **Đạt** |

---

## Đánh giá tổng kết Phase 3
- **Yêu cầu đã đạt:** Đạt 100% tất cả 11 tiêu chí kiểm chứng của TICKET-03 và Test Contract v1.2.
- **Hồi quy:** Tất cả các test hồi quy P1 và P2 đều đã được cập nhật tương thích với schema kho cá thể và cơ chế tính giá theo độ tươi.
- **Tính tất định:** Chạy cùng seed cho ra output byte-for-byte hoàn toàn đồng nhất.
- **Thời gian hoàn thành:** Đảm bảo thời gian gắn tag `phase-3` trước hạn chót 2:30.
