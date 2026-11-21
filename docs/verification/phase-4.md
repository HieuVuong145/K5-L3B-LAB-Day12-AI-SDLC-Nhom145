# Ma trận truy vết Phase 4 (TICKET-04 — Phát hành v1.0.0)

| AC | Nội dung yêu cầu | Cách kiểm chứng | Bằng chứng | Kết quả |
| :--- | :--- | :--- | :--- | :--- |
| **AC-P4-01** | Test Contract v1.3 & khai báo `bench_cmd`, `soak_cmd` | `game.contract.json` & `test_contract_version_13_and_commands` | [game.contract.json](../../game.contract.json), [test_suite.txt](../proof/phase-4/test_suite.txt) | **Đạt** |
| **AC-P4-02** | Benchmark có render đạt chuẩn | Chạy `python3 -m chonoi.bench --seed 42 --duration 30 --out docs/proof/phase-4/bench.json` | [bench.json](../proof/phase-4/bench.json) | **Đạt** |
| **AC-P4-03** | Ngưỡng Benchmark (avg ≥ 60 FPS, 1% low ≥ 30 FPS, load ≤ 10s) | Đọc `docs/proof/phase-4/bench.json` & `test_bench_produces_valid_metrics` | [bench.json](../proof/phase-4/bench.json) | **Đạt** |
| **AC-P4-04** | Cảnh báo nhận biết bằng chữ và biểu tượng | Giao diện hiển thị cảnh báo Cá Sấu, Oxy, Khách sắp giận kèm biểu tượng | [index.html](../../chonoi/web/index.html) | **Đạt** |
| **AC-P4-05** | Chế độ tương phản cao | Phím tắt H và nút toggle HUD trên web giao diện | [index.html](../../chonoi/web/index.html) | **Đạt** |
| **AC-P4-06** | Soak headless chạy 10 Ngày lặp kế hoạch D1-D5 | Chạy `python3 -m chonoi.soak --seed 7 --days 10 --out docs/proof/phase-4/soak.json` | [soak.json](../proof/phase-4/soak.json) | **Đạt** |
| **AC-P4-07** | Soak đạt days_completed = days và crashes = 0 | Đọc `docs/proof/phase-4/soak.json` & `test_soak_runs_and_produces_valid_json` | [soak.json](../proof/phase-4/soak.json) | **Đạt** |
| **AC-P4-08** | Chạy bản có giao diện từ clone sạch trong ≤ 3 lệnh | Tài liệu README.md hướng dẫn cài đặt & chạy | [README.md](../../README.md) | **Đạt** |
| **AC-P4-09** | Toàn bộ 95 test case xanh (100% OK) | Chạy `python3 -m unittest discover -s tests -v` | [test_suite.txt](../proof/phase-4/test_suite.txt) | **Đạt** |
| **AC-P4-10** | Đội ngũ hợp lệ 2 thành viên | `python3 tools/check_team.py` | [team_check.txt](../proof/phase-4/team_check.txt) | **Đạt** |

---

## Tổng kết Phase 4
- Hoàn thành đầy đủ các tiêu chí bàn giao v1.0.0.
- Khai báo Contract v1.3 chuẩn xác.
- Benchmark và Soak hoàn tất tự động không lỗi.
