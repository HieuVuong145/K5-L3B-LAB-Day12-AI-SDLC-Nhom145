"""Unit test cho cơ chế Độ tươi & Kho cá thể (Phase 3 — Contract v1.2 / TICKET-03)."""

import json
import os
import unittest

from chonoi.contract import load_contract
from chonoi.ids import IdAllocator
from chonoi.inputs import LiveInputs
from chonoi.inventory import read_inventory, write_inventory
from chonoi.errors import BadInput
from chonoi.rng import Streams
from chonoi.runner import run
from chonoi.sim.gather import GatherSim
from chonoi.sim.quan import QuanSim
from test_smoke_p1 import Workdir, read_jsonl, events, snapshots, write_json, frames, run_headless


class FreshnessTest(unittest.TestCase):
    def setUp(self):
        self.tuning = load_contract()["tuning"]

    def _make_gather(self, scenario=None):
        return GatherSim(
            tuning=self.tuning,
            scenario=scenario or {},
            streams=Streams(1),
            ids=IdAllocator(),
        )

    def _make_quan(self, scenario=None, inventory=None):
        return QuanSim(
            tuning=self.tuning,
            scenario=scenario or {},
            streams=Streams(1),
            ids=IdAllocator(),
            inventory=inventory,
        )

    # 1. Gather: hao tươi & ngưỡng 30
    def test_gather_exact_threshold_30_emits_spoiled(self):
        """Theo spec TICKET-03: cá thể bắt đầu đúng fresh 30 nên ươn ở bước đầu."""
        sim = self._make_gather({
            "hold": [{"id": "I1", "kind": "ca_linh", "fresh": 30.0}],
            "random_fish": False,
            "monsters": []
        })
        inp = LiveInputs()
        ev = sim.step(inp.advance())
        spoiled = [e for e in ev if e[0] == "spoiled"]
        self.assertEqual(len(spoiled), 1)
        self.assertEqual(spoiled[0][1], {
            "item_id": "I1",
            "kind": "ca_linh",
            "location": "hold"
        })
        self.assertLess(sim.hold[0]["fresh"], 30.0)

        # Bước tiếp theo không phát spoiled lần nữa (chỉ phát đúng 1 lần khi chuyển ngưỡng)
        ev2 = sim.step(inp.advance())
        self.assertEqual([e for e in ev2 if e[0] == "spoiled"], [])

    def test_gather_multiple_spoiled_sorted_by_id(self):
        sim = self._make_gather({
            "hold": [
                {"id": "I2", "kind": "ca_loc", "fresh": 30.0},
                {"id": "I1", "kind": "ca_linh", "fresh": 30.0}
            ]
        })
        inp = LiveInputs()
        ev = sim.step(inp.advance())
        spoiled = [e for e in ev if e[0] == "spoiled"]
        self.assertEqual(len(spoiled), 2)
        self.assertEqual(spoiled[0][1]["item_id"], "I1")
        self.assertEqual(spoiled[1][1]["item_id"], "I2")

    def test_gather_newly_collected_item_decays_from_next_step(self):
        sim = self._make_gather({
            "player": {"pos": [12.5, 0.0]},
            "nodes": [{"id": "N1", "kind": "bong_dien_dien", "pos": [12.0, 0.0], "regrow_ticks": 0}]
        })
        inp = LiveInputs()
        inp.set(interact=True)
        # Tick 1: hái nút, item mới thu hoạch có fresh = 100.0, chưa bị hao ở tick này
        sim.step(inp.advance())
        self.assertEqual(len(sim.hold), 1)
        self.assertEqual(sim.hold[0]["fresh"], 100.0)

        # Tick 2: bắt đầu hao từ bước sau: 100 - 0.5/60 = 99.992
        inp.set(interact=False)
        sim.step(inp.advance())
        self.assertLess(sim.hold[0]["fresh"], 100.0)
        self.assertAlmostEqual(sim.hold[0]["fresh"], 99.992, places=3)

    # 2. Quán: hao tươi & xử lý hàng ươn
    def test_quan_stock_decay_and_spoiled(self):
        sim = self._make_quan(scenario={
            "stock": [{"id": "I1", "kind": "ca_loc", "fresh": 30.0}],
            "random_customers": False
        })
        inp = LiveInputs()
        ev = sim.step(inp.advance())
        spoiled = [e for e in ev if e[0] == "spoiled"]
        self.assertEqual(len(spoiled), 1)
        self.assertEqual(spoiled[0][1], {
            "item_id": "I1",
            "kind": "ca_loc",
            "location": "stock"
        })
        self.assertLess(sim.stock[0]["fresh"], 30.0)

    def test_spoiled_items_cannot_be_used_for_cooking(self):
        # Kho chỉ có cá lóc đã ươn (fresh = 25 < 30) -> no_dish
        sim = self._make_quan(scenario={
            "stock": [{"id": "I1", "kind": "ca_loc", "fresh": 25.0}],
            "random_customers": True
        })
        inp = LiveInputs()
        for _ in range(120):
            ev = sim.step(inp.advance())
        self.assertIn("no_dish", [e[0] for e in ev])
        self.assertEqual(len(sim.customers), 0)

    def test_reservation_re_reserve_when_item_spoils(self):
        # I1 có fresh 30.0 (sẽ ươn sau 1 tick), I2 có fresh 90.0 (vẫn tươi)
        # Khách C1 giữ chỗ I1. Khi I1 ươn, nhả I1 và giữ lại I2.
        sim = self._make_quan(scenario={
            "random_customers": False,
            "customers": [{
                "id": "C1", "order_id": "O1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui",
                "state": "waiting", "order_tick": 0, "patience_ticks_left": 100,
                "reserved": ["I1"]
            }],
            "stock": [
                {"id": "I1", "kind": "ca_loc", "fresh": 30.0},
                {"id": "I2", "kind": "ca_loc", "fresh": 90.0}
            ]
        })
        inp = LiveInputs()
        ev = sim.step(inp.advance())
        self.assertIn("spoiled", [e[0] for e in ev])
        c = sim.customers[0]
        # Khách C1 đã được re-reserve sang I2
        self.assertEqual(c["reserved"], ["I2"])
        self.assertEqual(c["order_status"], "reserved")

    def test_reservation_fails_re_reserve_becomes_unfulfillable(self):
        # Kho chỉ có đúng I1 fresh 30.0. Khi I1 ươn, không còn cá thể thay thế -> unfulfillable
        sim = self._make_quan(scenario={
            "random_customers": False,
            "customers": [{
                "id": "C1", "order_id": "O1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui",
                "state": "waiting", "order_tick": 0, "patience_ticks_left": 100,
                "reserved": ["I1"]
            }],
            "stock": [
                {"id": "I1", "kind": "ca_loc", "fresh": 30.0}
            ]
        })
        inp = LiveInputs()
        ev = sim.step(inp.advance())
        self.assertIn("spoiled", [e[0] for e in ev])
        c = sim.customers[0]
        self.assertEqual(c["reserved"], [])
        self.assertEqual(c["order_status"], "unfulfillable")

    # 3. Giá theo độ tươi & làm tròn floor
    def test_price_calculation_with_freshness_and_tip(self):
        # Món ca_loc_nuong_trui listed_price = 60
        # Cá lóc có fresh = 80.0
        # base_price = floor(60 * 80.0 / 100) = 48
        # Phục vụ nhanh (> 50% patience) -> tip = floor(48 * 0.2) = 9
        # Tổng = 48 + 9 = 57
        sim = self._make_quan(scenario={
            "random_customers": False,
            "player": {"pos": [2.0, 8.0]},
            "customers": [{
                "id": "C1", "order_id": "O1", "table_id": "T1", "dish_id": "ca_loc_nuong_trui",
                "state": "waiting", "order_tick": 0, "patience_ticks_left": 3600,
                "reserved": ["I1"]
            }],
            "stock": [{"id": "I1", "kind": "ca_loc", "fresh": 80.005}]  # trừ 1 tick decay (0.25/60) -> 80.000
        })
        inp = LiveInputs()
        inp.set(interact=True)
        ev = sim.step(inp.advance())
        cook_start = [e for e in ev if e[0] == "cook_started"]
        self.assertEqual(len(cook_start), 1)
        self.assertEqual(cook_start[0][1]["base_price"], 48)
        self.assertEqual(len(cook_start[0][1]["items"]), 1)
        self.assertEqual(cook_start[0][1]["items"][0]["id"], "I1")

    # 4. Schema Contract v1.2: từ chối kho đếm (mã 2)
    def test_contract_v12_rejects_count_inventory(self):
        with Workdir() as w:
            count_inv = write_json(w.path("inv.json"), {"items": {"ca_loc": 2}})
            code, err = run_headless("--mode", "quan", "--seed", "1", "--ticks", "0",
                                     "--inventory", count_inv, "--out", w.path("q.jsonl"))
            self.assertEqual(code, 2)
            self.assertIn("đầu vào sai", err)

    def test_contract_v12_accepts_individual_inventory(self):
        with Workdir() as w:
            indiv_inv = write_json(w.path("inv.json"), {
                "items": [{"id": "I1", "kind": "ca_loc", "fresh": 100}]
            })
            code, err = run_headless("--mode", "quan", "--seed", "1", "--ticks", "0",
                                     "--inventory", indiv_inv, "--out", w.path("q.jsonl"))
            self.assertEqual(code, 0, err)
            stock = snapshots(read_jsonl(w.path("q.jsonl")))[0]["stock"]
            self.assertEqual(len(stock), 1)
            self.assertEqual(stock[0]["id"], "I1")
            self.assertEqual(stock[0]["kind"], "ca_loc")
            self.assertEqual(stock[0]["fresh"], 100.0)

    # 5. Smoke test bàn giao kho v1.2 theo kịch bản TICKET-03
    def test_smoke_handover_dock_gather_to_quan(self):
        """Để smoke bàn giao file: dùng fresh:100 và interact:true ở frame 0 để cập bến.
        Mở quan --inventory với file vừa ghi và --ticks 0. So chính xác id, kind và độ tươi."""
        with Workdir() as w:
            sc = write_json(w.path("sc.json"), {
                "gather": {
                    "hold": [{"id": "I1", "kind": "ca_linh", "fresh": 100.0}],
                    "random_fish": False,
                    "monsters": []
                }
            })
            inp = write_json(w.path("in.json"), frames({"tick": 0, "interact": True}))
            inv = w.path("inv.json")
            code, err = run_headless("--mode", "gather", "--seed", "1", "--ticks", "1",
                                     "--scenario", sc, "--inputs", inp, "--inventory-out", inv,
                                     "--out", w.path("g.jsonl"))
            self.assertEqual(code, 0, err)

            # File kho đã ghi
            with open(inv, encoding="utf-8") as f:
                saved = json.load(f)
            self.assertEqual(len(saved["items"]), 1)
            self.assertEqual(saved["items"][0]["id"], "I1")
            self.assertEqual(saved["items"][0]["kind"], "ca_linh")
            # 100 - 0.5/60 = 99.992
            self.assertEqual(saved["items"][0]["fresh"], 99.992)

            # Quán nạp file kho với --ticks 0
            code, err = run_headless("--mode", "quan", "--seed", "1", "--ticks", "0",
                                     "--inventory", inv, "--out", w.path("q.jsonl"))
            self.assertEqual(code, 0, err)
            q_stock = snapshots(read_jsonl(w.path("q.jsonl")))[0]["stock"]
            self.assertEqual(q_stock, saved["items"])


if __name__ == "__main__":
    unittest.main()
