"""Test Phase 2: cá bơi/sinh, Cá Sấu, vòng day + Shop + pause."""

import unittest

from chonoi.contract import load_contract
from chonoi.day import ShopSim
from chonoi.inputs import InputState, LiveInputs
from chonoi.runner import Session


def tuning():
    return load_contract()["tuning"]


def names(rows):
    return [r["name"] for r in rows]


def run_steps(session, steps):
    li = LiveInputs()
    rows = []
    for _ in range(steps):
        rows += session.step(li.advance())
    return rows


class Fish(unittest.TestCase):
    def test_fish_swim_and_age(self):
        s = Session("gather", tuning(), {}, 3)
        first = {f["id"]: list(f["pos"]) for f in s.snapshot()["fish"]}
        run_steps(s, 5)
        fish = {f["id"]: f for f in s.snapshot()["fish"]}
        moved = [fid for fid, pos in first.items() if fish[fid]["pos"] != pos]
        self.assertTrue(moved)
        self.assertEqual(fish[moved[0]]["age_ticks"], 5)

    def test_spawn_at_360_with_clearance(self):
        s = Session("gather", tuning(), {}, 5)
        rows = run_steps(s, 361)
        spawns = [r for r in rows if r["name"] == "fish_spawned"]
        self.assertEqual(len(spawns), 1)
        self.assertEqual(spawns[0]["tick"], 360)
        data = spawns[0]["data"]
        self.assertEqual(data["kind"], s.snapshot()["fish"][-1]["kind"])
        self.assertEqual(len(s.snapshot()["fish"]), 9)


class Monster(unittest.TestCase):
    def test_hit_loses_half_hold_lifo_and_sets_invuln(self):
        sc = {"player": {"pos": [60, 24]}, "hold": ["ca_loc", "bong_sung", "ca_linh", "keo_neo"]}
        s = Session("gather", tuning(), sc, 1)
        rows = run_steps(s, 1)
        hits = [r for r in rows if r["name"] == "monster_hit"]
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]["data"]["monster_id"], "M1")
        self.assertEqual(hits[0]["data"]["hp"], 2)
        self.assertEqual(hits[0]["data"]["lost"], ["keo_neo", "ca_linh"])
        self.assertEqual(s.snapshot()["player"]["invuln_ticks"], 90)
        monsters = s.snapshot()["monsters"]
        self.assertEqual(monsters[0]["state"], "recoil")
        rows = run_steps(s, 5)
        self.assertEqual([r for r in rows if r["name"] == "monster_hit"], [])


class Shop(unittest.TestCase):
    def test_buy_tiers_funds_and_close(self):
        sim = ShopSim(tuning(), {"money": 300, "earned": 300, "upgrades": {}, "active_upgrades": {}})
        idle = InputState((0.0, 0.0), {}, set())
        rows = sim.step(InputState((0.0, 0.0), {}, set(), "oxygen"))
        self.assertEqual([r[0] for r in rows], ["bought"])
        self.assertEqual(sim.money, 100)
        rows = sim.step(InputState((0.0, 0.0), {}, set(), "hp"))
        self.assertEqual(rows[0][0], "buy_failed")
        self.assertEqual(rows[0][1]["reason"], "funds")
        rows = sim.step(InputState((0.0, 0.0), {}, set(), "net"))
        self.assertEqual(rows[0][1]["reason"], "unknown")
        self.assertIsNotNone(idle)

    def test_buy_max_level(self):
        sim = ShopSim(tuning(), {"money": 10000, "earned": 10000, "upgrades": {}})
        for _ in range(2):
            self.assertEqual(sim.step(InputState((0.0, 0.0), {}, set(), "hp"))[0][0], "bought")
        self.assertEqual(sim.step(InputState((0.0, 0.0), {}, set(), "hp"))[0][1]["reason"], "max_level")


class Day(unittest.TestCase):
    def test_one_day_reaches_shop_and_completes(self):
        sc = {"quan": {"time_left_ticks": 2}}
        s = Session("day", tuning(), sc, 1, days=1)
        frames = [{"tick": 0, "interact": True}, {"tick": 3, "shop_done": True}]
        from chonoi.inputs import InputPlayer
        player = InputPlayer(frames)
        rows = []
        while not s.done and s.tick < 20:
            rows += s.step(player.advance(s.tick))
        got = names(rows)
        for name in ("day_start", "day_plan", "phase_start", "gather_end", "quan_end", "shop_end"):
            self.assertIn(name, got)
        end = s.end_row()
        self.assertEqual(end["reason"], "days_complete")
        self.assertEqual(end["days_completed"], 1)
        snap = s.snapshot()
        self.assertEqual(snap["day"], 1)
        self.assertIn("day_plan", snap)

    def test_pause_freezes_phase_and_resumes(self):
        s = Session("day", tuning(), {"quan": {"time_left_ticks": 1}}, 1, days=1)
        li = LiveInputs()
        li.set(pause=True)
        rows = s.step(li.advance())
        self.assertIn("paused", names(rows))
        frozen = s.sim.phase_tick
        li.set(pause=False)
        s.step(li.advance())
        self.assertEqual(s.sim.phase_tick, frozen)
        li.set(pause=True)
        rows = s.step(li.advance())
        self.assertIn("resumed", names(rows))
        self.assertEqual(s.sim.phase_tick, frozen + 1)


if __name__ == "__main__":
    unittest.main()