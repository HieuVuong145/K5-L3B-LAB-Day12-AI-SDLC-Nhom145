"""Soak headless: <soak_cmd> --seed 7 --days 10 --out soak.json

Chạy N Ngày trong một tiến trình headless bằng bot tất định.
Mỗi Ngày đi qua gather -> quan -> shop.
Kế hoạch D1–D5 lặp ở Ngày 6–10.
Tiền, tổng thu, uy tín, cấp nâng cấp, số Ngày và id cá thể tiếp tục xuyên suốt.

soak.json có: days, days_completed, crashes, results, duration_s.
results[]: [{"day": ..., "earned": ..., "reputation": ..., "score": ...}] tại lúc Shop đóng.
"""

import argparse
import json
import math
import os
import sys
import time

from .contract import load_contract
from .day import DaySim
from .errors import BadInput
from .ids import IdAllocator
from .inputs import LiveInputs
from .rng import Streams


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        self.print_usage(sys.stderr)
        sys.stderr.write(f"lỗi: {message}\n")
        sys.exit(2)


def _int(name):
    def conv(s):
        try:
            return int(s)
        except ValueError:
            raise argparse.ArgumentTypeError(f"{name} phải là số nguyên")
    return conv


class SoakBot:
    """Bot tất định điều khiển Út Sen qua gather -> quan -> shop."""

    def __init__(self, sim, tuning):
        self.sim = sim
        self.tuning = tuning
        self.inputs = LiveInputs()
        self.gather_ticks = 0
        self.last_phase = None

    def get_input(self):
        phase = self.sim.phase
        if phase != self.last_phase:
            self.last_phase = phase
            self.gather_ticks = 0

        move = [0.0, 0.0]
        interact = False
        buy = None
        shop_done = False

        if phase == "gather":
            self.gather_ticks += 1
            g = self.sim.gather
            px, pd = g.pos
            # Nếu giỏ còn chỗ và dưới 240 tick: bơi về phía cụm cây N1 (x=12, d=0) để hái bông điên điển
            if len(g.hold) < 2 and self.gather_ticks < 240:
                if px < 11.5:
                    move = [1.0, 0.0]
                elif px > 13.5:
                    move = [-1.0, 0.0]
                else:
                    move = [0.0, 0.0]
                    interact = True
            else:
                # Bơi về bến (x=2, d=0) và cập bến
                if px > 2.5:
                    move = [-1.0, 0.0]
                else:
                    move = [0.0, 0.0]
                    interact = True

        elif phase == "quan":
            q = self.sim.quan
            px, pz = q.pos

            # 1. Nếu đang bưng món trên tay: di chuyển tới bàn của khách cần món đó
            if q.hand:
                dish_id = q.hand.get("dish_id")
                target_table = None
                for c in q.customers:
                    if c.get("state") == "waiting" and c.get("dish_id") == dish_id:
                        target_table = c.get("table_id")
                        break
                if not target_table and q.customers:
                    target_table = q.customers[0].get("table_id")

                if target_table:
                    tbl = next((t for t in q.tables if t["id"] == target_table), None)
                    if tbl:
                        tx, tz = tbl["pos"]
                        dx, dz = tx - px, tz - pz
                        dist = math.hypot(dx, dz)
                        if dist <= q.interact_radius:
                            interact = True
                        else:
                            move = [dx / dist, dz / dist]
            else:
                # 2. Nếu có bếp đã nấu xong (ready): di chuyển tới nhấc món
                ready_stove = next((st for st in q.stoves if st.get("state") == "ready"), None)
                if ready_stove:
                    sx, sz = ready_stove["pos"]
                    dx, dz = sx - px, sz - pz
                    dist = math.hypot(dx, dz)
                    if dist <= q.interact_radius:
                        interact = True
                    else:
                        move = [dx / dist, dz / dist]
                else:
                    # 3. Nếu có khách đang chờ đã giữ chỗ và bếp rảnh: di chuyển tới bếp để nấu
                    waiting_cust = [c for c in q.customers if c.get("state") == "waiting" and c.get("order_status") == "reserved"]
                    idle_stove = next((st for st in q.stoves if st.get("state") == "idle"), None)
                    if waiting_cust and idle_stove:
                        sx, sz = idle_stove["pos"]
                        dx, dz = sx - px, sz - pz
                        dist = math.hypot(dx, dz)
                        if dist <= q.interact_radius:
                            interact = True
                        else:
                            move = [dx / dist, dz / dist]

        elif phase == "shop":
            s = self.sim.shop
            if s.money >= 200:
                buy = "oxygen"
            shop_done = True

        self.inputs.set(move=move, buy=buy, interact=interact, shop_done=shop_done)
        return self.inputs.advance()


def run_soak(seed: int, days: int, out_path: str) -> dict:
    start_time = time.perf_counter()
    contract = load_contract()
    tuning = contract["tuning"]

    streams = Streams(seed)
    ids = IdAllocator()
    sim = DaySim(tuning, {}, streams, ids, days=days)
    bot = SoakBot(sim, tuning)

    results = []
    crashes = 0
    last_completed = 0

    try:
        max_total_ticks = days * 36000  # Ngưỡng an toàn tối đa
        tick = 0
        while not sim.done and tick < max_total_ticks:
            inp = bot.get_input()
            sim.step(inp)
            tick += 1

            if sim.days_completed > last_completed:
                last_completed = sim.days_completed
                # Ghi nhận kết quả tại thời điểm Shop đóng
                earned = sim._earned
                rep = sim._reputation
                score = int(earned + 100 * math.floor(rep))
                results.append({
                    "day": last_completed,
                    "earned": earned,
                    "reputation": round(rep, 2),
                    "score": score
                })
    except Exception as e:
        sys.stderr.write(f"soak crash: {e}\n")
        crashes = 1

    duration_s = round(time.perf_counter() - start_time, 3)

    data = {
        "days": days,
        "days_completed": sim.days_completed,
        "crashes": crashes,
        "results": results,
        "duration_s": duration_s
    }

    # Ghi nguyên tử ra out_path
    tmp_path = out_path + ".tmp"
    os.makedirs(os.path.dirname(os.path.abspath(out_path)) or ".", exist_ok=True)
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, out_path)

    return data


def main(argv=None) -> int:
    p = _Parser(prog="chonoi.soak")
    p.add_argument("--seed", required=True, type=_int("seed"))
    p.add_argument("--days", required=True, type=_int("days"))
    p.add_argument("--out", required=True)
    a = p.parse_args(argv)

    if a.days < 1:
        sys.stderr.write("đầu vào sai: --days phải >= 1\n")
        return 2

    try:
        data = run_soak(a.seed, a.days, a.out)
        sys.stdout.write(f"Soak hoàn tất: {data['days_completed']}/{data['days']} ngày, {data['crashes']} lỗi, {data['duration_s']}s -> {a.out}\n")
        return 0 if data["crashes"] == 0 and data["days_completed"] == a.days else 1
    except BadInput as e:
        sys.stderr.write(f"đầu vào sai: {e}\n")
        return 2
    except Exception as e:
        sys.stderr.write(f"lỗi: {e}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
