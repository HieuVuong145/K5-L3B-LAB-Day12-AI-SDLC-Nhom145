"""Unit test luật `gather` lát 1: oxy, dive/surface, ngạt -> choke, ngất, giỏ LIFO/sức chứa.

Chạy: PYTHONPATH=tests:. python -m unittest discover -s tests -v
"""

import unittest

from chonoi.contract import load_contract
from chonoi.inputs import LiveInputs
from chonoi.runner import Session


def tuning():
    return load_contract()["tuning"]


def gather_session(scenario, seed=1):
    return Session("gather", tuning(), scenario, seed)


def names(rows):
    return [r["name"] for r in rows]


class Oxygen(unittest.TestCase):
    def test_oxygen_drains_one_tick_per_tick_underwater(self):
        s = gather_session({"player": {"pos": [50, 10], "oxygen_ticks": 10}})
        li = LiveInputs()
        li.set(move=[0, 1])  # bơi xuống: giữ dưới nước
        for _ in range(5):
            s.step(li.advance())
        self.assertEqual(s.snapshot()["player"]["oxygen_ticks"], 5)

    def test_oxygen_refills_at_surface_and_stops_at_max(self):
        g = tuning()["gather"]
        s = gather_session({"player": {"pos": [50, 10], "oxygen_ticks": 1}})
        li = LiveInputs()
        li.set(move=[0, -1])  # bơi lên
        for _ in range(400):
            s.step(li.advance())
            if s.snapshot()["player"]["at_surface"]:
                break
        p = s.snapshot()["player"]
        self.assertTrue(p["at_surface"])
        self.assertGreater(p["oxygen_ticks"], 1)
        self.assertEqual(p["zero_oxy_ticks"], 0)
        for _ in range(400):
            s.step(li.advance())
        self.assertEqual(s.snapshot()["player"]["oxygen_ticks"], s.sim.oxygen_max)
        self.assertEqual(g["surface_depth"], s.sim.t["surface_depth"])

    def test_oxygen_empty_event_fires_once(self):
        s = gather_session({"player": {"pos": [50, 10], "oxygen_ticks": 1}})
        li = LiveInputs()
        li.set(move=[0, 0])
        first = names(s.step(li.advance()))
        second = names(s.step(li.advance()))
        self.assertIn("oxygen_empty", first)
        self.assertNotIn("oxygen_empty", second)
        self.assertEqual(s.snapshot()["player"]["oxygen_ticks"], 0)


class Zones(unittest.TestCase):
    def test_dive_and_surface_events_carry_pos(self):
        g = tuning()["gather"]
        s = gather_session({"player": {"pos": [50, 0]}})
        li = LiveInputs()
        li.set(move=[0, 1])
        dive = None
        for _ in range(120):
            for row in s.step(li.advance()):
                if row["name"] == "dive":
                    dive = row
            if dive:
                break
        self.assertIsNotNone(dive, "phải có sự kiện dive khi lặn qua surface_depth")
        self.assertGreater(dive["data"]["pos"][1], g["surface_depth"])
        li.set(move=[0, -1])
        surface = None
        for _ in range(240):
            for row in s.step(li.advance()):
                if row["name"] == "surface":
                    surface = row
            if surface:
                break
        self.assertIsNotNone(surface, "phải có sự kiện surface khi nổi lên")
        self.assertLessEqual(surface["data"]["pos"][1], g["surface_depth"])

    def test_no_zone_event_while_staying_underwater(self):
        s = gather_session({"player": {"pos": [50, 10]}})
        li = LiveInputs()
        li.set(move=[1, 0])
        rows = []
        for _ in range(30):
            rows += s.step(li.advance())
        self.assertEqual([n for n in names(rows) if n in ("dive", "surface")], [])


class Choke(unittest.TestCase):
    def test_choke_after_interval_costs_one_hp(self):
        g = tuning()["gather"]
        s = gather_session({"player": {"pos": [50, 10], "oxygen_ticks": 0,
                                       "zero_oxy_ticks": g["choke_interval_ticks"] - 1,
                                       "hp": g["hp_max"]}})
        li = LiveInputs()
        li.set(move=[0, 0])
        rows = s.step(li.advance())
        self.assertEqual(names(rows), ["choke"])
        self.assertEqual(rows[0]["data"]["hp"], g["hp_max"] - 1)
        self.assertEqual(s.snapshot()["player"]["zero_oxy_ticks"], 0)
        self.assertEqual(s.snapshot()["player"]["hp"], g["hp_max"] - 1)

    def test_faint_clears_hold_and_ends_with_reason_fainted(self):
        g = tuning()["gather"]
        s = gather_session({"player": {"pos": [50, 10], "oxygen_ticks": 0,
                                       "zero_oxy_ticks": g["choke_interval_ticks"] - 1,
                                       "hp": 1},
                            "hold": ["ca_loc", "bong_sung"]})
        li = LiveInputs()
        li.set(move=[0, 0])
        rows = s.step(li.advance())
        self.assertEqual(names(rows), ["choke", "faint", "gather_end"])
        lost_kinds = [it["kind"] if isinstance(it, dict) else it for it in rows[1]["data"]["lost"]]
        self.assertEqual(lost_kinds, ["bong_sung", "ca_loc"])  # LIFO: mất món mới nhất trước
        self.assertEqual(rows[1]["data"]["hp"], 0)
        self.assertEqual(rows[2]["data"]["reason"], "fainted")
        self.assertEqual(rows[2]["data"]["inventory"], {"items": []})
        self.assertEqual(s.sim.hold, [])
        self.assertEqual(s.snapshot()["player"]["hp"], 0)
        self.assertTrue(s.done)

    def test_surfacing_resets_choke_counter(self):
        g = tuning()["gather"]
        s = gather_session({"player": {"pos": [50, 2], "oxygen_ticks": 0,
                                       "zero_oxy_ticks": 5}})
        li = LiveInputs()
        li.set(move=[0, -1])
        for _ in range(120):
            s.step(li.advance())
            if s.snapshot()["player"]["at_surface"]:
                break
        p = s.snapshot()["player"]
        self.assertTrue(p["at_surface"])
        self.assertEqual(p["zero_oxy_ticks"], 0)
        self.assertGreater(p["oxygen_ticks"], 0)


class Hold(unittest.TestCase):
    def test_add_to_hold_is_lifo_and_respects_capacity(self):
        g = tuning()["gather"]
        sim = gather_session({}).sim
        self.assertTrue(sim._add_to_hold("bong_sung"))
        self.assertTrue(sim._add_to_hold("ca_loc"))
        self.assertEqual(sim.hold, ["bong_sung", "ca_loc"], "LIFO: món mới nhất ở cuối")
        for _ in range(int(g["hold_capacity"]) - 2):
            self.assertTrue(sim._add_to_hold("ca_loc"))
        self.assertTrue(sim._hold_full())
        self.assertFalse(sim._add_to_hold("ca_loc"), "giỏ đầy thì không nhận thêm")
        self.assertEqual(len(sim.hold), int(g["hold_capacity"]))


if __name__ == "__main__":
    unittest.main()