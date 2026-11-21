"""Unit test cho luật chơi Mở Quán (Quan — Lát 3 và Lát 4)."""

import json
import unittest

from chonoi.contract import load_contract
from chonoi.ids import IdAllocator
from chonoi.inputs import LiveInputs
from chonoi.rng import Streams
from chonoi.sim.quan import QuanSim


class QuanTest(unittest.TestCase):
    def setUp(self):
        self.tuning = load_contract()["tuning"]

    def _make_sim(self, scenario=None, inventory=None):
        return QuanSim(
            tuning=self.tuning,
            scenario=scenario or {},
            streams=Streams(42),
            ids=IdAllocator(),
            inventory=inventory,
        )

    # --- Lát 3: Khách đến, chọn món, giữ chỗ, hết kiên nhẫn --------------------
    def test_customer_arrives_and_reserves_stock(self):
        sim = self._make_sim(
            scenario={"random_customers": True},
            inventory={"ca_loc": 5}
        )
        inp = LiveInputs()

        # Trước tick 120: chưa có khách
        for _ in range(119):
            sim.step(inp.advance())
        self.assertEqual(len(sim.customers), 0)

        # Tại tick 120: khách đầu tiên tới
        ev = sim.step(inp.advance())
        arrived = [e for e in ev if e[0] == "customer_arrived"]
        self.assertEqual(len(arrived), 1)
        self.assertEqual(arrived[0][1]["dish_id"], "ca_loc_nuong_trui")
        self.assertEqual(len(sim.customers), 1)
        c = sim.customers[0]
        self.assertEqual(c["state"], "waiting")
        self.assertEqual(sim.reserved, {"ca_loc": 1})

    def test_no_dish_when_stock_empty(self):
        # Kho rỗng -> không nấu được món nào -> phát no_dish
        sim = self._make_sim(
            scenario={"random_customers": True},
            inventory={}
        )
        inp = LiveInputs()
        for _ in range(119):
            sim.step(inp.advance())

        ev = sim.step(inp.advance())
        self.assertIn("no_dish", [e[0] for e in ev])
        self.assertEqual(len(sim.customers), 0)

    def test_customer_timeout_leaves_and_penalizes_reputation(self):
        sim = self._make_sim(scenario={
            "random_customers": False,
            "customers": [{
                "id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui",
                "state": "waiting", "order_tick": 0, "patience_ticks_left": 2,
                "reserved": {"ca_loc": 1}
            }],
            "stock": {"ca_loc": 2}
        })
        inp = LiveInputs()
        self.assertEqual(sim.reserved.get("ca_loc"), 1)

        # Tick 1: patience 2 -> 1
        sim.step(inp.advance())
        self.assertEqual(len(sim.customers), 1)

        # Tick 2: patience 1 -> 0 -> rời bàn
        ev = sim.step(inp.advance())
        left = [e for e in ev if e[0] == "customer_left"]
        self.assertEqual(len(left), 1)
        self.assertEqual(left[0][1]["order_id"], "C1")
        self.assertEqual(left[0][1]["reason"], "patience")
        self.assertEqual(sim.reputation, 2.5)  # 3.0 + (-0.5)
        self.assertEqual(sim.reserved.get("ca_loc", 0), 0)
        self.assertEqual(len(sim.customers), 0)

    # --- Lát 4: Nấu, bưng, phục vụ, thanh toán, đóng ca ------------------------
    def test_full_cooking_serving_and_payment_flow(self):
        # Người chơi đứng cạnh bếp B1 [2, 8]
        sim = self._make_sim(scenario={
            "random_customers": False,
            "player": {"pos": [2.0, 8.0]},
            "customers": [{
                "id": "C1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui",
                "state": "waiting", "order_tick": 0, "patience_ticks_left": 3600,
                "reserved": {"ca_loc": 1}
            }],
            "stock": {"ca_loc": 1}
        })
        inp = LiveInputs()

        # 1. Bấm interact tại bếp B1 để bắt đầu nấu
        inp.set(interact=True)
        ev = sim.step(inp.advance())
        cook_start = [e for e in ev if e[0] == "cook_started"]
        self.assertEqual(len(cook_start), 1)
        self.assertEqual(cook_start[0][1]["stove_id"], "B1")
        self.assertEqual(cook_start[0][1]["dish_id"], "ca_loc_nuong_trui")
        self.assertEqual(cook_start[0][1]["base_price"], 60)
        self.assertEqual(sim.stock.get("ca_loc"), 0)
        self.assertEqual(sim.stoves[0]["state"], "cooking")

        # 2. Đợi bếp nấu chín: cook_s = 6s = 360 tick
        cook_ticks = int(round(sim.menu["ca_loc_nuong_trui"]["cook_s"] * 60))
        inp.set(interact=False)
        ready_events = []
        for _ in range(cook_ticks):
            ready_events.extend([e for e in sim.step(inp.advance()) if e[0] == "dish_ready"])
        self.assertEqual(len(ready_events), 1)
        self.assertEqual(sim.stoves[0]["state"], "ready")

        # 3. Bấm interact tại bếp để lấy món lên tay
        inp.set(interact=True)
        ev = sim.step(inp.advance())
        picked = [e for e in ev if e[0] == "dish_picked"]
        self.assertEqual(len(picked), 1)
        self.assertIsNotNone(sim.hand)
        self.assertEqual(sim.hand["dish_id"], "ca_loc_nuong_trui")
        self.assertEqual(sim.stoves[0]["state"], "idle")

        # 4. Người chơi nhả nút, di chuyển tới bàn T1 [9, 2]
        inp.set(interact=False)
        sim.step(inp.advance())
        sim.pos = [9.0, 2.0]

        # 5. Bấm interact tại bàn để phục vụ
        inp.set(interact=True)
        ev = sim.step(inp.advance())
        served = [e for e in ev if e[0] == "served"]
        self.assertEqual(len(served), 1)
        self.assertEqual(served[0][1]["order_id"], "C1")
        self.assertEqual(served[0][1]["table_id"], "T1")
        # Phục vụ nhanh (patience còn > 50%) -> có boa: 60 * 0.2 = 12
        self.assertEqual(served[0][1]["tip"], 12)
        self.assertIsNone(sim.hand)
        self.assertEqual(sim.customers[0]["state"], "eating")

        # 6. Khách ăn xong: eat_s = 10s = 600 tick
        eat_ticks = int(round(sim.t["eat_s"] * 60))
        inp.set(interact=False)
        paid_events = []
        for _ in range(eat_ticks):
            paid_events.extend([e for e in sim.step(inp.advance()) if e[0] == "paid"])
        self.assertEqual(len(paid_events), 1)
        self.assertEqual(paid_events[0][1]["amount"], 72)  # 60 + 12
        self.assertEqual(paid_events[0][1]["reason"], "finished_eating")
        self.assertEqual(sim.money, 72)
        self.assertEqual(sim.earned, 72)
        self.assertEqual(sim.reputation, 3.2)  # 3.0 + 0.2
        self.assertEqual(len(sim.customers), 0)

    def test_closing_settlement(self):
        # Hết giờ ca: khách đang ăn được thanh toán ngay, khách chờ rời không trừ uy tín
        sim = self._make_sim(scenario={
            "random_customers": False,
            "time_left_ticks": 1,
            "customers": [
                {
                    "id": "C1", "table_id": "T1", "dish_id": "goi_bong_sung",
                    "state": "eating", "eat_ticks_left": 500, "base_price": 40, "tip": 8
                }
            ],
            "stock": {}
        })
        inp = LiveInputs()
        ev = sim.step(inp.advance())

        # Kiểm tra khách ăn trả tiền khi closing
        paid = [e for e in ev if e[0] == "paid"]
        self.assertEqual(len(paid), 1)
        self.assertEqual(paid[0][1]["reason"], "closing")
        self.assertEqual(paid[0][1]["amount"], 48)

        # Uy tín tăng do boa của C1 (3.0 + 0.2 = 3.2)
        self.assertEqual(sim.reputation, 3.2)

        # Kiểm tra quan_end
        q_end = [e for e in ev if e[0] == "quan_end"]
        self.assertEqual(len(q_end), 1)
        self.assertEqual(q_end[0][1]["reason"], "time")
        self.assertEqual(q_end[0][1]["money"], 48)
        self.assertTrue(sim.done)


if __name__ == "__main__":
    unittest.main()
