"""Unit test cho luật chơi Lặn & Hái (Gather — Lát 1 và Lát 2)."""

import json
import unittest

from chonoi.contract import load_contract
from chonoi.ids import IdAllocator
from chonoi.inputs import LiveInputs
from chonoi.rng import Streams
from chonoi.sim.gather import GatherSim


class GatherTest(unittest.TestCase):
    def setUp(self):
        self.tuning = load_contract()["tuning"]

    def _make_sim(self, scenario=None):
        return GatherSim(
            tuning=self.tuning,
            scenario=scenario or {},
            streams=Streams(1),
            ids=IdAllocator(),
        )

    # --- Lát 1: Bơi, lặn, nổi, oxy, ngạt, ngất ----------------------------------
    def test_dive_and_surface_events(self):
        sim = self._make_sim({"player": {"pos": [20.0, 0.0]}})
        inp = LiveInputs()

        # Bơi xuống
        inp.set(move=[0.0, 1.0])
        events = sim.step(inp.advance())
        # Sau 1 vài tick bơi xuống, độ sâu vượt 0.5m -> phát dive
        dive_events = [e for e in events if e[0] == "dive"]
        while not dive_events and sim.pos[1] <= 1.0:
            events = sim.step(inp.advance())
            dive_events = [e for e in events if e[0] == "dive"]
        self.assertTrue(len(dive_events) >= 1)
        self.assertEqual(dive_events[0][0], "dive")
        self.assertGreater(sim.pos[1], 0.5)

        # Bơi ngược lên mặt nước
        inp.set(move=[0.0, -1.0])
        surface_events = []
        while not surface_events and sim.pos[1] > 0.0:
            events = sim.step(inp.advance())
            surface_events = [e for e in events if e[0] == "surface"]
        self.assertTrue(len(surface_events) >= 1)
        self.assertLessEqual(sim.pos[1], 0.5)

    def test_oxygen_consumption_and_choke(self):
        # Người chơi ở dưới nước với oxy chỉ còn 2 tick
        sim = self._make_sim({
            "player": {"pos": [20.0, 5.0], "oxygen_ticks": 2, "hp": 3, "zero_oxy_ticks": 0}
        })
        inp = LiveInputs()

        # Tick 1: oxy 2 -> 1
        ev1 = sim.step(inp.advance())
        self.assertEqual(sim.oxygen_ticks, 1)

        # Tick 2: oxy 1 -> 0, phát oxygen_empty
        ev2 = sim.step(inp.advance())
        self.assertEqual(sim.oxygen_ticks, 0)
        self.assertIn("oxygen_empty", [e[0] for e in ev2])
        self.assertEqual(sim.zero_oxy_ticks, 1)

        # 59 tick tiếp theo: ngạt chạm 60 -> phát choke, -1 Máu
        choke_events = []
        for _ in range(59):
            ev = sim.step(inp.advance())
            choke_events.extend([e for e in ev if e[0] == "choke"])
        self.assertEqual(len(choke_events), 1)
        self.assertEqual(sim.hp, 2)
        self.assertEqual(choke_events[0][1]["hp"], 2)

    def test_faint_clears_hold_lifo(self):
        # Máu 1, giỏ có đồ, ngạt lần nữa sẽ ngất
        sim = self._make_sim({
            "player": {"pos": [20.0, 5.0], "oxygen_ticks": 0, "hp": 1, "zero_oxy_ticks": 59},
            "hold": ["ca_loc", "bong_sung", "ca_linh"]
        })
        inp = LiveInputs()
        events = sim.step(inp.advance())

        faint_ev = [e for e in events if e[0] == "faint"]
        self.assertEqual(len(faint_ev), 1)
        self.assertEqual(faint_ev[0][1]["cause"], "choke")
        # LIFO: nhặt sau bỏ trước -> ["ca_linh", "bong_sung", "ca_loc"]
        self.assertEqual(faint_ev[0][1]["lost"], ["ca_linh", "bong_sung", "ca_loc"])
        self.assertEqual(sim.hold, [])
        self.assertTrue(sim.done)
        self.assertEqual(sim.reason, "fainted")
        self.assertEqual(sim.inventory_items(), {})

    # --- Lát 2: Hái nút, Bắt cá -----------------------------------------------
    def test_gather_node_success(self):
        # N1 ở [12, 0], người chơi đứng ở [12.5, 0] (khoảng cách 0.5 <= 2.0)
        sim = self._make_sim({
            "player": {"pos": [12.5, 0.0]},
            "nodes": [{"id": "N1", "kind": "bong_dien_dien", "pos": [12.0, 0.0], "regrow_ticks": 0}]
        })
        inp = LiveInputs()
        inp.set(interact=True)
        events = sim.step(inp.advance())

        gather_ev = [e for e in events if e[0] == "gather"]
        self.assertEqual(len(gather_ev), 1)
        self.assertEqual(gather_ev[0][1], {"node_id": "N1", "kind": "bong_dien_dien", "amount": 1})
        self.assertEqual(sim.hold, ["bong_dien_dien"])
        # Nút phải bắt đầu đếm regrow_ticks = 20 * 60 = 1200
        self.assertEqual(sim.nodes[0]["regrow_ticks"], 1200)

    def test_gather_node_underwater_fails(self):
        # Người chơi ở độ sâu d = 2.0 (dưới nước) -> không được hái
        sim = self._make_sim({
            "player": {"pos": [12.0, 2.0]},
            "nodes": [{"id": "N1", "kind": "bong_dien_dien", "pos": [12.0, 0.0], "regrow_ticks": 0}]
        })
        inp = LiveInputs()
        inp.set(interact=True)
        events = sim.step(inp.advance())

        gather_ev = [e for e in events if e[0] == "gather"]
        self.assertEqual(len(gather_ev), 0)
        self.assertEqual(sim.hold, [])

    def test_gather_node_hold_full(self):
        # Giỏ đã đầy (12/12)
        sim = self._make_sim({
            "player": {"pos": [12.0, 0.0]},
            "hold": ["ca_loc"] * 12,
            "nodes": [{"id": "N1", "kind": "bong_dien_dien", "pos": [12.0, 0.0], "regrow_ticks": 0}]
        })
        inp = LiveInputs()
        inp.set(interact=True)
        events = sim.step(inp.advance())

        hold_full_ev = [e for e in events if e[0] == "hold_full"]
        self.assertEqual(len(hold_full_ev), 1)
        self.assertEqual(hold_full_ev[0][1], {
            "action": "gather",
            "node_id": "N1",
            "required": 1,
            "free": 0
        })
        self.assertEqual(len(sim.hold), 12)
        # Nút không bị hái, vẫn ready
        self.assertEqual(sim.nodes[0]["regrow_ticks"], 0)

    def test_catch_fish_success(self):
        # F1 ở [15, 5], kind ca_linh (yield=3)
        sim = self._make_sim({
            "player": {"pos": [15.0, 5.0]},
            "fish": [{"id": "F1", "kind": "ca_linh", "pos": [15.0, 5.0], "heading_deg": 0}]
        })
        inp = LiveInputs()
        inp.set(catch=True)
        events = sim.step(inp.advance())

        catch_ev = [e for e in events if e[0] == "fish_caught"]
        self.assertEqual(len(catch_ev), 1)
        self.assertEqual(catch_ev[0][1], {"fish_id": "F1", "kind": "ca_linh", "yield": 3})
        self.assertEqual(sim.hold, ["ca_linh", "ca_linh", "ca_linh"])
        # Đàn cá F1 đã bị bắt và xóa khỏi sim.fish
        self.assertEqual(sim.fish, [])
        # Cooldown = 0.5s * 60 = 30 tick
        self.assertEqual(sim.catch_cd_ticks, 30)

    def test_catch_fish_at_surface_fails(self):
        # Người chơi ở mặt nước (d = 0.0) -> không thể bấm catch bắt cá
        sim = self._make_sim({
            "player": {"pos": [15.0, 0.0]},
            "fish": [{"id": "F1", "kind": "ca_linh", "pos": [15.0, 1.0], "heading_deg": 0}]
        })
        inp = LiveInputs()
        inp.set(catch=True)
        events = sim.step(inp.advance())

        self.assertEqual([e for e in events if e[0] == "fish_caught"], [])
        self.assertEqual(sim.hold, [])

    def test_catch_fish_on_cooldown_fails(self):
        sim = self._make_sim({
            "player": {"pos": [15.0, 5.0], "catch_cd_ticks": 10},
            "fish": [{"id": "F1", "kind": "ca_linh", "pos": [15.0, 5.0], "heading_deg": 0}]
        })
        inp = LiveInputs()
        inp.set(catch=True)
        events = sim.step(inp.advance())

        self.assertEqual([e for e in events if e[0] == "fish_caught"], [])
        self.assertEqual(len(sim.fish), 1)

    def test_catch_fish_hold_full(self):
        # Giỏ đã có 10 món, cá linh cần 3 chỗ -> free = 2 < 3 -> phát hold_full
        sim = self._make_sim({
            "player": {"pos": [15.0, 5.0]},
            "hold": ["ca_loc"] * 10,
            "fish": [{"id": "F1", "kind": "ca_linh", "pos": [15.0, 5.0], "heading_deg": 0}]
        })
        inp = LiveInputs()
        inp.set(catch=True)
        events = sim.step(inp.advance())

        hold_full_ev = [e for e in events if e[0] == "hold_full"]
        self.assertEqual(len(hold_full_ev), 1)
        self.assertEqual(hold_full_ev[0][1], {
            "action": "catch",
            "fish_id": "F1",
            "required": 3,
            "free": 2
        })
        # Đàn cá giữ nguyên, không đặt cooldown
        self.assertEqual(len(sim.fish), 1)
        self.assertEqual(sim.catch_cd_ticks, 0)
        self.assertEqual(len(sim.hold), 10)


if __name__ == "__main__":
    unittest.main()
