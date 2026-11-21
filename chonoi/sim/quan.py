"""Buổi tối — Mở Quán: đi lại, khách, nấu, phục vụ, trả tiền, đóng ca.

Đã làm: lát 3 (khách theo lịch, chọn món, giữ chỗ, kiên nhẫn, customer_left/no_dish) và
lát 4 (interact bếp/bàn, cook_started, dish_ready, dish_picked, served, paid, boa, đóng ca).
Số liệu đọc từ game.contract.json; ngẫu nhiên chỉ qua Streams.
"""

import math

from ..ids import id_key, sort_by_id
from .ramp import ramp_velocity

TICK = 60.0


class QuanSim:
    mode = "quan"
    phase = "quan"

    def __init__(self, tuning, scenario, streams, ids, inventory=None):
        t = tuning["quan"]
        self.t = t
        self.menu = tuning["menu"]
        self.rng = streams
        self.ids = ids
        p = scenario.get("player", {})
        self.pos = list(p.get("pos", t["start_pos"]))
        self.vel = [float(c) for c in p.get("vel", [0.0, 0.0])]
        self._tgt = None
        self._ramp_left = 0
        # kho: --inventory HOẶC scenario.stock (cả hai -> cli báo mã 2)
        self.stock = dict(inventory if inventory is not None else scenario.get("stock", {}))
        self.hand = scenario.get("hand")
        if isinstance(self.hand, str):
            self.hand = {"dish_id": self.hand, "order_id": None}
        self.time_left_ticks = scenario.get("time_left_ticks", int(round(t["duration_s"] * 60)))
        self.reputation = scenario.get("reputation", t["reputation_initial"])
        self.stoves = [dict(s, state=s.get("state", "idle"), dish=s.get("dish"), order_id=s.get("order_id"),
                            cook_ticks_left=s.get("cook_ticks_left", 0), ready_ticks=s.get("ready_ticks", 0))
                       for s in self._merge(t["stoves"], scenario.get("stoves", []))]
        self.tables = self._merge(t["tables"], scenario.get("tables", []))
        self.patience_ticks = int(round(t["patience_s"] * TICK))
        self.eat_ticks = int(round(t["eat_s"] * TICK))
        self.spawn_every = max(1, int(round(t["customer_interval_s"] * TICK)))
        self.first_customer_tick = int(t["first_customer_tick"])
        self.random_customers = bool(scenario.get("random_customers", True))
        # chế độ day truyền menu_ids = món trong kế hoạch; quán riêng dùng cả menu
        self.menu_ids = [d for d in (scenario.get("menu_ids") or sorted(self.menu)) if d in self.menu]
        self.tip_rate = float(t["tip_rate"])
        self.tip_min_ratio = float(t["tip_min_patience_ratio"])
        self.tip_reputation = float(t["tip_reputation"])
        self.steps = 0
        self.served = 0
        self.left = 0
        self.tips = 0
        self.reserved = {}
        self.customers = []
        for c in scenario.get("customers", []):
            cust = dict(c)
            dish = cust.get("dish_id")
            cust.setdefault("state", "waiting")
            cust.setdefault("order_tick", 0)
            cust.setdefault("order_id", None)
            cust.setdefault("order_status", "reserved")
            cust.setdefault("patience_ticks_left", self.patience_ticks)
            cust.setdefault("patience_max", self.patience_ticks)
            cust.setdefault("reserved", dict(self.menu.get(dish, {}).get("recipe", {})))
            cust.setdefault("price", int(self.menu.get(dish, {}).get("price", 0)))
            cust.setdefault("tip", 0)
            cust.setdefault("stove_id", None)
            self.customers.append(cust)
            self.ids.reserve(cust["id"])
            if cust.get("order_id"):
                self.ids.reserve(cust["order_id"])
            self._add_reserved(cust.get("reserved") or {})
        for st in self.stoves:
            if st.get("order_id"):
                self.ids.reserve(st["order_id"])
        self.money = 0
        self.earned = 0
        self.shift_earned = 0
        self.done = False
        self.reason = None

    @staticmethod
    def _merge(defaults, updates):
        by_id = {d["id"]: dict(d) for d in defaults}
        for u in updates:
            if u["id"] not in by_id:
                from ..errors import BadInput
                raise BadInput(f"id bếp/bàn không tồn tại: {u['id']}")
            by_id[u["id"]].update(u)
        return sort_by_id(list(by_id.values()))

    def snapshot(self) -> dict:
        occupied = {c["table_id"]: c["id"] for c in self.customers}
        return {
            "player": {"pos": self.pos, "vel": self.vel},
            "stock": {k: self.stock[k] for k in sorted(self.stock) if self.stock[k] > 0},
            "hand": self.hand,
            "stoves": [{k: s.get(k) for k in ("id", "pos", "state", "dish", "order_id",
                                              "cook_ticks_left", "ready_ticks")} for s in self.stoves],
            "tables": [{"id": tb["id"], "pos": tb["pos"], "customer_id": occupied.get(tb["id"])}
                       for tb in self.tables],
            "customers": sort_by_id(self.customers),
            "served": self.served, "left": self.left,
        }
    # --- kho / giữ chỗ ---------------------------------------------------------
    def _add_reserved(self, recipe):
        for kind, n in recipe.items():
            self.reserved[kind] = self.reserved.get(kind, 0) + int(n)

    def _release(self, recipe):
        for kind, n in recipe.items():
            self.reserved[kind] = max(0, self.reserved.get(kind, 0) - int(n))

    def _available(self, kind) -> int:
        return max(0, int(self.stock.get(kind, 0)) - int(self.reserved.get(kind, 0)))

    def _can_cook(self, dish_id) -> bool:
        recipe = self.menu.get(dish_id, {}).get("recipe", {})
        return bool(recipe) and all(self._available(k) >= int(n) for k, n in recipe.items())

    def _free_table(self):
        used = {c["table_id"] for c in self.customers}
        for tb in self.tables:
            if tb["id"] not in used:
                return tb
        return None

    def _pick_dish(self):
        options = [d for d in sorted(self.menu_ids) if self._can_cook(d)]
        if not options:
            return None
        return options[self.rng.get("quan_order").randrange(len(options))]

    def _due_customer_tick(self) -> bool:
        if self.steps < self.first_customer_tick:
            return False
        return (self.steps - self.first_customer_tick) % self.spawn_every == 0

    def _maybe_spawn(self, events):
        if not self.random_customers or not self._due_customer_tick():
            return
        table = self._free_table()
        if table is None:
            return                       # hết bàn: bỏ lượt, không sự kiện
        dish = self._pick_dish()
        if dish is None:
            events.append(("no_dish", {}))
            return
        recipe = dict(self.menu[dish]["recipe"])
        cust = {"id": self.ids.new("C"), "table_id": table["id"], "dish_id": dish, "state": "waiting",
                "order_tick": self.steps, "order_id": self.ids.new("O"), "order_status": "reserved",
                "patience_ticks_left": self.patience_ticks, "patience_max": self.patience_ticks,
                "reserved": recipe, "price": int(self.menu[dish]["price"]), "tip": 0, "stove_id": None}
        self.customers.append(cust)
        self._add_reserved(recipe)

    def _clamp_rep(self, value):
        lo = float(self.t.get("reputation_min", 0))
        hi = float(self.t.get("reputation_max", 5))
        return min(hi, max(lo, value))

    def _customer_left(self, cust, events, reason="patience"):
        self.customers.remove(cust)
        self._release(cust.get("reserved") or {})
        cust["reserved"] = {}
        self.left += 1
        if reason == "patience":
            self.reputation = self._clamp_rep(self.reputation + float(self.t.get("left_reputation_delta", 0.0)))
        events.append(("customer_left", {"customer_id": cust["id"], "table_id": cust["table_id"],
                                         "reason": reason}))

    # --- bếp / bàn -------------------------------------------------------------
    def _customer_by_order(self, order_id):
        for c in self.customers:
            if c.get("order_id") == order_id:
                return c
        return None

    def _customer_at(self, table_id):
        for c in self.customers:
            if c["table_id"] == table_id:
                return c
        return None

    def _oldest_order(self):
        orders = [c for c in self.customers
                  if c.get("state") == "waiting" and c.get("order_status") == "reserved"]
        orders.sort(key=lambda c: (int(c.get("order_tick", 0)), id_key(c["table_id"])))
        return orders[0] if orders else None

    def _interact_target(self):
        r = float(self.t["interact_radius"])
        best = None
        for st in self.stoves:
            d = math.dist(self.pos, st["pos"])
            if d <= r:
                key = (d, 0, id_key(st["id"]))
                if best is None or key < best[0]:
                    best = (key, "stove", st)
        for tb in self.tables:
            d = math.dist(self.pos, tb["pos"])
            if d <= r:
                key = (d, 1, id_key(tb["id"]))
                if best is None or key < best[0]:
                    best = (key, "table", tb)
        return (best[1], best[2]) if best else (None, None)

    def _use_stove(self, st, events):
        if st["state"] == "ready":
            if self.hand is None:
                self.hand = {"dish_id": st["dish"], "order_id": st["order_id"]}
                cust = self._customer_by_order(st["order_id"])
                if cust is not None:
                    cust["order_status"] = "picked"
                events.append(("dish_picked", {"stove_id": st["id"], "dish_id": st["dish"],
                                                "order_id": st["order_id"]}))
                st.update(state="idle", dish=None, order_id=None, cook_ticks_left=0, ready_ticks=0)
            return
        if st["state"] != "idle":
            return
        order = self._oldest_order()
        if order is None:
            return
        dish = order["dish_id"]
        for kind, n in self.menu[dish]["recipe"].items():
            self.stock[kind] = max(0, int(self.stock.get(kind, 0)) - int(n))
        self._release(order.get("reserved") or {})
        order["reserved"] = {}
        order["order_status"] = "cooking"
        order["stove_id"] = st["id"]
        st.update(state="cooking", dish=dish, order_id=order["order_id"],
                  cook_ticks_left=int(round(self.menu[dish]["cook_s"] * TICK)), ready_ticks=0)
        events.append(("cook_started", {"stove_id": st["id"], "order_id": order["order_id"],
                                         "dish_id": dish, "table_id": order["table_id"]}))

    def _use_table(self, tb, events):
        cust = self._customer_at(tb["id"])
        if cust is None or cust.get("state") != "waiting" or not isinstance(self.hand, dict):
            return
        if self.hand.get("dish_id") != cust.get("dish_id") or self.hand.get("order_id") != cust.get("order_id"):
            return
        pmax = int(cust.get("patience_max") or self.patience_ticks)
        ratio = int(cust.get("patience_ticks_left", 0)) / float(pmax)
        tip = int(math.floor(int(cust.get("price", 0)) * self.tip_rate)) if ratio >= self.tip_min_ratio else 0
        self.hand = None
        cust["state"] = "eating"
        cust["eat_ticks_left"] = self.eat_ticks
        cust["tip"] = tip
        cust["order_status"] = "served"
        events.append(("served", {"table_id": tb["id"], "customer_id": cust["id"],
                                   "dish_id": cust["dish_id"], "order_id": cust["order_id"]}))
    # --- vòng chạy -------------------------------------------------------------
    def _tick_stoves(self, events):
        for st in sort_by_id(self.stoves):
            if st["state"] == "cooking":
                st["cook_ticks_left"] = max(0, int(st["cook_ticks_left"]) - 1)
                if st["cook_ticks_left"] == 0:
                    st["state"] = "ready"
                    st["ready_ticks"] = 0
                    cust = self._customer_by_order(st.get("order_id"))
                    if cust is not None:
                        cust["order_status"] = "ready"
                    events.append(("dish_ready", {"stove_id": st["id"], "dish_id": st["dish"],
                                                   "order_id": st.get("order_id")}))
            elif st["state"] == "ready":
                st["ready_ticks"] = int(st.get("ready_ticks", 0)) + 1

    def _tick_eating(self, events):
        for c in sort_by_id([c for c in self.customers if c.get("state") == "eating"]):
            c["eat_ticks_left"] = max(0, int(c.get("eat_ticks_left", 0)) - 1)
            if c["eat_ticks_left"] == 0:
                self._pay(c, events)

    def _pay(self, cust, events):
        price = int(cust.get("price", 0))
        tip = int(cust.get("tip", 0))
        total = price + tip
        self.money += total
        self.earned += total
        self.shift_earned += total
        if tip > 0:
            self.tips += tip
            self.reputation = self._clamp_rep(self.reputation + self.tip_reputation)
        self.customers.remove(cust)
        self.served += 1
        events.append(("paid", {"customer_id": cust["id"], "table_id": cust["table_id"],
                                "dish_id": cust.get("dish_id"), "price": price, "tip": tip,
                                "money": self.money}))

    def _close_shift(self, events):
        for c in sort_by_id([c for c in self.customers if c.get("state") == "eating"]):
            self._pay(c, events)
        for c in sort_by_id(list(self.customers)):
            self._customer_left(c, events, reason="closing")
        for st in self.stoves:
            st.update(state="idle", dish=None, order_id=None, cook_ticks_left=0, ready_ticks=0)
        self.hand = None
        self.reserved = {}

    def _quan_end(self, events):
        events.append(("quan_end", {"reason": "time", "money": self.money, "earned": self.earned,
                                    "shift_earned": self.shift_earned, "reputation": self.reputation,
                                    "served": self.served, "left": self.left, "tips": self.tips}))

    def step(self, inp):
        events = []
        self.steps += 1
        self.time_left_ticks = max(0, self.time_left_ticks - 1)
        self._tick_stoves(events)
        self._tick_eating(events)
        for c in sort_by_id(self.customers):
            if c.get("state") == "waiting" and int(c.get("order_tick", 0)) < self.steps:
                c["patience_ticks_left"] = max(0, int(c.get("patience_ticks_left", 0)) - 1)
        self._move(inp)
        if inp.pressed("interact"):
            kind, target = self._interact_target()
            if kind == "stove":
                self._use_stove(target, events)
            elif kind == "table":
                self._use_table(target, events)
        if self.time_left_ticks > 0:
            for c in sort_by_id([c for c in self.customers
                                 if c.get("state") == "waiting" and int(c.get("patience_ticks_left", 0)) <= 0]):
                self._customer_left(c, events, reason="patience")
            self._maybe_spawn(events)
        else:
            self._close_shift(events)
            self.done = True
            self.reason = "time"
            self._quan_end(events)
        return events

    def _move(self, inp):
        speed = self.t["walk_speed"]
        mx, mz = inp.move
        self.vel = ramp_velocity(self, (mx * speed, mz * speed), int(self.t.get("ramp_max_ticks", 6)))
        b = self.t["bounds"]
        for i, axis in enumerate(("x", "z")):
            self.pos[i] += self.vel[i] / TICK
            lo, hi = b[axis]
            if self.pos[i] <= lo:
                self.pos[i], self.vel[i] = lo, max(0.0, self.vel[i])
            elif self.pos[i] >= hi:
                self.pos[i], self.vel[i] = hi, min(0.0, self.vel[i])
