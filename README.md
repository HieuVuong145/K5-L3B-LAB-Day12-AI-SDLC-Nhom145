# Day 12 — AI SDLC: Quán Ăn Chợ Nổi (Nhom145)

> **Nhóm 2 người (đã được chấp thuận trong `docs/clarify.md`)** · Dùng AI để xây game 2D qua **4 phase** trong **3 giờ**: Út Sen lặn bắt cá, hái rau trên mặt nước rồi tối mở quán phục vụ khách trên nhà bè Má Tư.
> **Yêu cầu từng phase mở đúng mốc giờ tại lab board:** **[Chợ Nổi Lab](https://claude.ai/artifact/E35v787wSx2wDgPTNhMVDg)**.

## Bắt đầu nhanh (Tối đa 3 lệnh từ clone sạch)

```bash
git clone https://github.com/HieuVuong145/K5-L3B-LAB-Day12-AI-SDLC-Nhom145.git && cd K5-L3B-LAB-Day12-AI-SDLC-Nhom145
PYTHONPATH=tests:. python3 -m unittest discover -s tests -v
python3 -m chonoi.live --mode gather
```

## Cách chơi & Phím điều khiển

Mở trình duyệt tại địa chỉ in ra (mặc định `http://127.0.0.1:8000/`):
- **Buổi sáng (`gather`):** `python3 -m chonoi.live --mode gather [--inventory-out kho.json]`
  - `WASD` hoặc `phím mũi tên`: Bơi (nhìn ngang, độ sâu $d$ tăng khi bơi xuống).
  - `E`: Cập bến (khi ở mạn thuyền bên trái) hoặc Hái nút cây trên mặt nước ($d \le 0.5\,\text{m}$).
  - `Space`: Bắt đàn cá khi lặn dưới nước ($d > 0.5\,\text{m}$).
  - `R`: Chơi lại từ đầu.
- **Buổi tối (`quan`):** `python3 -m chonoi.live --mode quan --inventory docs/contracts/inventory.sample.json`
  - `WASD`: Đi lại trong quán (nhìn từ trên xuống).
  - `E`: Tương tác với Bếp B1 (nấu món, nhấc món chín lên tay) hoặc Bàn T1 (phục vụ khách).
  - `R`: Chơi lại từ đầu.

## Cách tính điểm (Scoring)

Điểm số được tính toán tự động ở mọi snapshot và dòng end theo công thức chuẩn của Test Contract:
$$\text{Score} = \text{Earned} + 100 \times \lfloor \text{Reputation} \rfloor$$
- `Earned`: Tổng tiền thu được từ bán món và tiền boa của khách trong lượt.
- `Reputation`: Điểm uy tín của quán (khởi đầu 3.0, tối đa 5.0, tối thiểu 0.0; phục vụ nhanh được cộng boa và tăng uy tín, để khách hết kiên nhẫn bỏ đi bị trừ 0.5 uy tín).

## Kiểm thử tự động (1 lệnh duy nhất)

```bash
PYTHONPATH=tests:. python3 -m unittest discover -s tests -v
```
Toàn bộ 47 unit tests bao phủ Test Contract, kiểm tra danh sách thành viên, chuyển động, lặn/hái và phục vụ quán đều đạt màu xanh (PASS).

## Bắt buộc & Bàn giao Phase

1. **Repo chung:** Repo fork public tại [HieuVuong145/K5-L3B-LAB-Day12-AI-SDLC-Nhom145](https://github.com/HieuVuong145/K5-L3B-LAB-Day12-AI-SDLC-Nhom145).
2. **Cam kết đóng góp:** Cả 2 thành viên đều commit bằng tài khoản GitHub thật của mình (`HieuVuong145` và `ngdinhtruong28`).
3. **Danh sách thành viên:** Đã điền đầy đủ và kiểm tra khớp trong [`TEAM.md`](TEAM.md) và [`game.contract.json`](game.contract.json).
4. **Gắn tag phase:** `phase-1` gắn tại commit hoàn thành Phase 1 trước 1:00.
5. **Ghi chép tối thiểu:** [`docs/verification/phase-1.md`](docs/verification/phase-1.md), [`docs/plan/phase-1.md`](docs/plan/phase-1.md), [`docs/clarify.md`](docs/clarify.md), [`docs/ai-usage-log.md`](docs/ai-usage-log.md), [`docs/standup.md`](docs/standup.md), [`docs/members/HieuVuong145.md`](docs/members/HieuVuong145.md), [`docs/members/ngdinhtruong28.md`](docs/members/ngdinhtruong28.md).

## Sáng tạo của nhóm (Phase 1)

Ở Phase 1, nhóm tập trung ưu tiên tối đa vào **sự chuẩn xác và độ ổn định của luật lõi** (làm lõi đúng trước, sáng tạo sau theo mục 1 của PRD-0):
- Xây dựng thêm bộ 15 unit tests chuyên biệt trong `tests/test_gather.py` và `tests/test_quan.py` bao phủ triệt để các góc cạnh của luồng gameplay (như giải hòa ID theo `id_key`, kiểm soát LIFO của giỏ khi ngất, tính boa theo tỷ lệ kiên nhẫn còn lại, và dọn ca khi hết giờ).
- Đảm bảo tính tất định 100% qua Streams RNG và hoàn thành tích hợp hai tiến trình headless đúng chuẩn.
