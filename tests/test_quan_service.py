"""Unit test quán lát 4: interact bếp/bàn, nấu, bưng, phục vụ, trả tiền + boa, đóng ca."""

import unittest

from chonoi.contract import load_contract
from chonoi.inputs import LiveInputs
from chonoi.runner import Session


def tuning():
    return load_contract()["tuning"]


def quan_session(scenario, seed=1):
    return Session("quan", tuning(), scenario, seed)


def names(rows):
    return [r["name"] for r in rows]


def stove(sim, stove_id="B1"):
    return [st for st in sim.stoves if st["id"] == stove_id][0]


class Service(unittest.TestCase):
    def test_cook_pick_serve_pay_with_tip(self):
        sc = {"stock": {"ca_loc": 3, "bong_sung": 6}, "random_customers": False,
              "player": {"pos": [2, 8]},
              "customers": [{"id": "C1", "table_id": "T1", "dish_id": "goi_bong_sung",
                              "patience_ticks_left": 3600, "order_tick": 0}]}
        s = quan_session(sc)
        li = LiveInputs()
        li.set(interact=True)
        rows = s.step(li.advance())
        li.set(interact=False)
        s.step(li.advance())
        self.assertEqual(names(rows), ["cook_started"])
        self.assertEqual(s.sim.stock["bong_sung"], 4)
        self.assertEqual(s.sim.reserved.get("bong_sung", 0), 0)
        self.assertEqual(stove(s.sim)["state"], "cooking")
        self.assertEqual(stove(s.sim)["cook_ticks_left"], 239)  # đã qua 1 bước nhả phím
        for _ in range(240):
            s.step(li.advance())
        self.assertEqual(stove(s.sim)["state"], "ready")
        li.set(interact=True)
        rows = s.step(li.advance())
        li.set(interact=False)
        self.assertEqual(names(rows), ["dish_picked"])
        self.assertEqual(s.sim.hand["dish_id"], "goi_bong_sung")
        s.sim.pos = [9, 2]
        li.set(interact=True)
        rows = s.step(li.advance())
        li.set(interact=False)
        self.assertEqual(names(rows), ["served"])
        self.assertIsNone(s.sim.hand)
        self.assertEqual(s.snapshot()["customers"][0]["state"], "eating")
        for _ in range(600):
            rows = s.step(li.advance())
        self.assertEqual(names(rows), ["paid"])
        self.assertEqual(s.snapshot()["customers"], [])
        self.assertEqual(rows[0]["data"]["price"], 40)
        self.assertEqual(rows[0]["data"]["tip"], 8)
        self.assertEqual(s.sim.money, 48)
        self.assertAlmostEqual(s.snapshot()["reputation"], 3.2)

    def test_no_tip_when_patience_low_at_serve(self):
        sc = {"stock": {"bong_sung": 2}, "random_customers": False,
              "player": {"pos": [9, 2]}, "hand": "goi_bong_sung",
              "customers": [{"id": "C1", "table_id": "T1", "dish_id": "goi_bong_sung",
                              "patience_ticks_left": 100, "patience_max": 3600, "order_tick": 0}]}
        s = quan_session(sc)
        li = LiveInputs()
        li.set(interact=True)
        rows = s.step(li.advance())
        self.assertEqual(names(rows), ["served"])
        cust = s.snapshot()["customers"][0]
        self.assertEqual(cust["tip"], 0)
        for _ in range(600):
            rows = s.step(li.advance())
        self.assertEqual(rows[0]["data"]["tip"], 0)
        self.assertEqual(s.sim.money, 40)

    def test_interact_stove_before_table_when_both_in_range(self):
        sc = {"stock": {"bong_sung": 2}, "random_customers": False,
              "player": {"pos": [9, 8]},
              "customers": [{"id": "C1", "table_id": "T1", "dish_id": "goi_bong_sung",
                              "patience_ticks_left": 3600, "order_tick": 0}]}
        s = quan_session(sc)
        s.sim.stoves[0]["pos"] = [9, 8]
        s.sim.tables[0]["pos"] = [9, 8]
        li = LiveInputs()
        li.set(interact=True)
        rows = s.step(li.advance())
        self.assertEqual(names(rows), ["cook_started"])


class Closing(unittest.TestCase):
    def test_closing_pays_eater_even_at_final_tick(self):
        sc = {"stock": {}, "random_customers": False, "time_left_ticks": 2,
              "customers": [{"id": "C1", "table_id": "T1", "dish_id": "goi_bong_sung",
                              "state": "eating", "eat_ticks_left": 500, "price": 40, "tip": 8,
                              "patience_ticks_left": 3000, "order_status": "served"}]}
        s = quan_session(sc)
        li = LiveInputs()
        rows = []
        for _ in range(2):
            rows += s.step(li.advance())
        self.assertIn("paid", names(rows))
        end = [r for r in rows if r["name"] == "quan_end"][0]["data"]
        self.assertEqual(end["served"], 1)
        self.assertEqual(s.sim.money, 48)
        self.assertTrue(s.done)

    def test_closing_waiter_leaves_without_reputation_penalty(self):
        sc = {"stock": {}, "random_customers": False, "time_left_ticks": 1,
              "customers": [{"id": "C1", "table_id": "T1", "dish_id": "goi_bong_sung",
                              "patience_ticks_left": 3600, "order_tick": 0}]}
        s = quan_session(sc)
        li = LiveInputs()
        rows = s.step(li.advance())
        left = [r for r in rows if r["name"] == "customer_left"]
        self.assertEqual(left[0]["data"]["reason"], "closing")
        self.assertAlmostEqual(s.snapshot()["reputation"], 3.0)
        self.assertEqual([r for r in rows if r["name"] == "quan_end"][0]["data"]["left"], 1)


if __name__ == "__main__":
    unittest.main()