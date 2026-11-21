# Clarify — câu hỏi và câu trả lời (PO ghi, cả nhóm dùng chung)

| # | Ngày giờ | Câu hỏi | Trả lời / giả định | Ai quyết |
|---|---|---|---|---|
| 1 | 2026-11-21 09:50 | Nhóm có được phép làm 2 người không và cần điều chỉnh kiểm tra thành viên như thế nào? | Được phép làm nhóm 2 người (Vương Toàn Minh Hiếu & Nguyễn Đình Trường). Đặt `team_size: 2` trong `game.contract.json`, điều chỉnh `tools/check_team.py` và `tests/test_team_check.py` cho phép quy mô nhóm từ 2–6 thành viên. | Giảng viên / PO |
| 2 | 2026-11-21 13:05 | Độ chính xác làm tròn số thực của độ tươi (`fresh`) giữa file kho JSON và dòng sự kiện JSONL? | Dùng làm tròn 3 chữ số thập phân (`round(v, 3)`) qua hàm `_clean` để giữ độ chính xác float, đảm bảo so sánh đúng ngưỡng 30.0 và đồng nhất byte-for-byte. | Nhóm thống nhất theo Test Contract v1.2 |
