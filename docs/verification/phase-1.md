# Ma trận truy vết Phase 1 (PRD-0)

| AC | Cách kiểm chứng | Bằng chứng (link `docs/proof/phase-1/...`) | Kết quả (đạt / chưa đạt — ghi trung thực) |
|---|---|---|---|
| AC-P1-01: Bơi, chặn mép, lặn/nổi | Unit test `test_move_*`, `test_dive_and_surface_events` | [test_suite.txt](docs/proof/phase-1/test_suite.txt) | Đạt |
| AC-P1-02: Tiêu thụ oxy, ngạt & ngất | Unit test `test_oxygen_consumption_and_choke`, `test_faint_clears_hold_lifo` | [test_suite.txt](docs/proof/phase-1/test_suite.txt) | Đạt |
| AC-P1-03: Hái nút trên mặt nước | Unit test `test_gather_node_success`, `test_gather_node_hold_full`, `test_gather_node_underwater_fails` | [test_suite.txt](docs/proof/phase-1/test_suite.txt) | Đạt |
| AC-P1-04: Bắt cá khi lặn & hồi chiêu | Unit test `test_catch_fish_success`, `test_catch_fish_hold_full`, `test_catch_fish_at_surface_fails` | [test_suite.txt](docs/proof/phase-1/test_suite.txt) | Đạt |
| AC-P1-05: Cập bến xuất kho nguyên tử | Unit test `test_inv_01_gather_writes_inventory_quan_reads_it` & chạy headless thật | [inventory_sample.json](docs/proof/phase-1/inventory_sample.json) | Đạt |
| AC-P1-06: Khách đến, giữ kho, no_dish | Unit test `test_customer_arrives_and_reserves_stock`, `test_no_dish_when_stock_empty` | [test_suite.txt](docs/proof/phase-1/test_suite.txt) | Đạt |
| AC-P1-07: Khách hết kiên nhẫn trừ uy tín | Unit test `test_customer_timeout_leaves_and_penalizes_reputation` | [test_suite.txt](docs/proof/phase-1/test_suite.txt) | Đạt |
| AC-P1-08: Bếp nấu, bưng bê, phục vụ & boa | Unit test `test_full_cooking_serving_and_payment_flow` | [test_suite.txt](docs/proof/phase-1/test_suite.txt) | Đạt |
| AC-P1-09: Đóng ca & thanh toán dứt điểm | Unit test `test_closing_settlement` | [test_suite.txt](docs/proof/phase-1/test_suite.txt) | Đạt |
| AC-P1-10: Kiểm tra thành viên TEAM.md | Chạy `python3 tools/check_team.py` | [team_check.txt](docs/proof/phase-1/team_check.txt) | Đạt |
| AC-P1-11: Tích hợp 2 tiến trình headless | Headless gather xuất kho -> headless quan đọc kho | [quan_sample.jsonl](docs/proof/phase-1/quan_sample.jsonl) | Đạt |

## Đánh giá ngắn
- **Yêu cầu nào đạt:** Đạt 100% tất cả 11 tiêu chí kiểm chứng cốt lõi của PRD-0 và Test Contract v1.0. Toàn bộ 47 unit test pass.
- **Yêu cầu chưa đạt:** Không có.
- **Điều cần chỉnh cho phase sau:** Tiếp tục duy trì quy trình TDD, phân tách lát cắt rõ ràng và đối chiếu schema trước khi viết logic sim.
