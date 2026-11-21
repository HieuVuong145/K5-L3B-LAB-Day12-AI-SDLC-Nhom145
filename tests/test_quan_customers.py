"""Unit test luật `quan` lát 3: khách đến theo lịch, chọn món, giữ nguyên liệu, kiên nhẫn, rời bàn.

Chạy: PYTHONPATH=tests:. python -m unittest discover -s tests -v
"""

import unittest

from chonoi.contract import load_contract
from chonoi.inputs import LiveInputs
from chonoi.runner import Session


def tuning():
    return load_contract()["tuning"]


def quan_session(scenario, seed=1):
    return Session("quan", tuning(), scenario, seed)


def run_steps(session, steps):
    li = LiveInputs()
    rows = []
    for _ in range(steps):
        rows += session.step(li.advance())
    return rows


def names(rows, only=None):
    return [r["name"] for r in rows if only is None or r["name"] == only]


class Arrival(unittest.TestCase):
    def test_first_customer_at_tick_120_reserves_recipe(self):
        q = tuning()["quan"]
        s = quan_session({"stock": {"ca_loc": 3, "bong_sung": 6}})
        self.assertEqual(s.snapshot()["customers"], [])
        run_steps(s, int(q["first_customer_tick"]))
        cust = s.snapshot()["customers"]
        self.assertEqual(len(cust), 1)
        c = cust[0]
        self.assertEqual(c["table_id"], "T1")
        self.assertEqual(c["state"], "waiting")
        self.assertEqual(c["patience_ticks_left"], int(round(q["patience_s"] * 60)))
        self.assertEqual(c["order_tick"], int(q["first_customer_tick"]))
        recipe = tuning()["menu"][c["dish_id"]]["recipe"]
        for kind, n in recipe.items():
            self.assertEqual(s.sim.reserved[kind], n, kind)
        # giữ chỗ không trừ kho vật lý
        st = s.snapshot()["stock"]
        counts = {k: sum(1 for it in st if it["kind"] == k) for k in ("bong_sung", "ca_loc")} if isinstance(st, list) else st
        self.assertEqual(counts, {"bong_sung": 6, "ca_loc": 3})

    def test_no_customer_before_the_first_tick(self):
        q = tuning()["quan"]
        s = quan_session({"stock": {"ca_loc": 3, "bong_sung": 6}})
        run_steps(s, int(q["first_customer_tick"]) - 1)
        self.assertEqual(s.snapshot()["customers"], [])

    def test_dish_choice_is_deterministic_per_seed(self):
        sc = {"stock": {"ca_loc": 10, "bong_sung": 20, "bong_dien_dien": 5, "ca_linh": 10}}
        a = quan_session(sc, seed=7)
        b = quan_session(sc, seed=7)
        run_steps(a, 120)
        run_steps(b, 120)
        self.assertEqual(a.snapshot()["customers"][0]["dish_id"], b.snapshot()["customers"][0]["dish_id"])

    def test_random_customers_false_disables_spawning(self):
        s = quan_session({"stock": {"ca_loc": 3, "bong_sung": 6}, "random_customers": False})
        rows = run_steps(s, 130)
        self.assertEqual(s.snapshot()["customers"], [])
        self.assertNotIn("no_dish", names(rows))


class Patience(unittest.TestCase):
    def test_patience_decreases_from_the_step_after_arrival(self):
        s = quan_session({"stock": {"ca_loc": 3, "bong_sung": 6}})
        run_steps(s, 120)
        p0 = s.snapshot()["customers"][0]["patience_ticks_left"]
        run_steps(s, 10)
        self.assertEqual(s.snapshot()["customers"][0]["patience_ticks_left"], p0 - 10)

    def test_zero_patience_leaves_releases_ingredients_and_costs_reputation(self):
        sc = {"stock": {"bong_sung": 2},
              "customers": [{"id": "C1", "table_id": "T1", "dish_id": "goi_bong_sung",
                              "patience_ticks_left": 2, "order_tick": 0}]}
        s = quan_session(sc)
        rep0 = s.snapshot()["reputation"]
        self.assertEqual(s.sim.reserved.get("bong_sung"), 2)
        rows = run_steps(s, 2)
        self.assertEqual(names(rows, "customer_left"), ["customer_left"])
        self.assertEqual(s.snapshot()["customers"], [])
        self.assertEqual(s.sim.reserved.get("bong_sung", 0), 0)
        self.assertAlmostEqual(s.snapshot()["reputation"], rep0 - 0.5)
        self.assertEqual(s.sim.left, 1)

    def test_patience_clamped_at_zero_before_shift_end(self):
        sc = {"stock": {"bong_sung": 2},
              "customers": [{"id": "C1", "table_id": "T1", "dish_id": "goi_bong_sung",
                              "patience_ticks_left": 1, "order_tick": 0}],
              "time_left_ticks": 1}
        s = quan_session(sc)
        rows = run_steps(s, 1)
        self.assertTrue(s.done)
        self.assertIn("quan_end", names(rows))


class NoDish(unittest.TestCase):
    def test_no_dish_when_stock_cannot_cover_any_recipe(self):
        s = quan_session({"stock": {}})
        rows = run_steps(s, 120)
        self.assertEqual(names(rows, "no_dish").count("no_dish"), 1)
        self.assertEqual([r["tick"] for r in rows if r["name"] == "no_dish"], [120])
        self.assertEqual(s.snapshot()["customers"], [])

    def test_occupied_table_skips_turn_without_event(self):
        sc = {"stock": {"bong_sung": 20},
              "customers": [{"id": "C%d" % i, "table_id": "T%d" % i, "dish_id": "goi_bong_sung",
                              "patience_ticks_left": 9999, "order_tick": 0} for i in (1, 2, 3, 4)]}
        s = quan_session(sc)
        rows = run_steps(s, 120)
        self.assertEqual(len(s.snapshot()["customers"]), 4)
        self.assertNotIn("no_dish", names(rows))


if __name__ == "__main__":
    unittest.main()