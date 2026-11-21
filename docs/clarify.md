# Clarify — câu hỏi và câu trả lời (PO ghi, cả nhóm dùng chung)

| # | Ngày giờ | Câu hỏi | Trả lời / giả định | Ai quyết |
|---|---|---|---|---|
| 1 | 2026-11-21 09:50 | Nhóm có được phép làm 2 người không và cần điều chỉnh kiểm tra thành viên như thế nào? | Được phép làm nhóm 2 người (Vương Toàn Minh Hiếu & Nguyễn Đình Trường). Đặt `team_size: 2` trong `game.contract.json`, điều chỉnh `tools/check_team.py` và `tests/test_team_check.py` cho phép quy mô nhóm từ 2–6 thành viên. | Giảng viên / PO |
| 2 | 2026-11-21 13:05 | Độ chính xác làm tròn số thực của độ tươi (`fresh`) giữa file kho JSON và dòng sự kiện JSONL? | Dùng làm tròn 3 chữ số thập phân (`round(v, 3)`) qua hàm `_clean` để giữ độ chính xác float, đảm bảo so sánh đúng ngưỡng 30.0 và đồng nhất byte-for-byte. | Nhóm thống nhất theo Test Contract v1.2 |
| 3 | 2026-11-21 14:10 | Quy ước lặp kế hoạch ngày khi chạy soak vượt quá 5 Ngày? | Khi số ngày > 5, kế hoạch lặp lại chu kỳ D1–D5 (Ngày 6 dùng kế hoạch Ngày 1, Ngày 7 dùng Ngày 2, ...) theo quy định của TICKET-04. | PO / Nhóm thống nhất |
| 4 | 2026-11-21 14:15 | Cách đo lường benchmark trên môi trường không có sẵn màn hình hiển thị? | `chonoi.bench` ưu tiên chạy headless browser khi có Chrome, đồng thời hỗ trợ fallback mô phỏng đo chu kỳ render nhằm đảm bảo chạy tin cậy trên mọi môi trường CI. | Nhóm thống nhất |
