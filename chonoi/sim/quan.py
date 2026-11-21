"""Buổi tối — Mở Quán: đi lại, khách, nấu, phục vụ, trả tiền, đóng ca.

Đã làm: lát 3 (khách theo lịch, chọn món, giữ chỗ theo ID cá thể, độ tươi, kiên nhẫn, customer_left/no_dish) và
lát 4 (interact bếp/bàn, cook_started với giá theo độ tươi, dish_ready, dish_picked, served, paid, boa, đóng ca).
Số liệu đọc từ game.contract.json; ngẫu nhiên chỉ qua Streams.
"""

import math

from ..ids import id_key, sort_by_id
from .ramp import ramp_velocity

TICK = 60.0


class StockList(list):
    def __getitem__(self, key):
        if isinstance(key, str):
            return sum(1 for it in self if it.get("kind") == key)
        return super().__getitem__(key)

    def get(self, key, default=0):
        if isinstance(key, str):
            c = sum(1 for it in self if it.get("kind") == key)
            return c if c > 0 else default
        return default


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

        self.freshness = tuning.get("freshness", {
            "initial": 100, "gather_decay_per_s": 0.5, "quan_decay_per_s": 0.25, "spoiled_below": 30
        })
        self.decay_per_tick = float(self.freshness.get("quan_decay_per_s", 0.25)) / TICK
        self.spoiled_below = float(self.freshness.get("spoiled_below", 30))
        self.flood = dict(tuning.get("flood") or {})
        if scenario.get("flood", {}).get("active"):
            self.flood["active"] = True

        # kho: --inventory HOẶC scenario.stock
        raw_stock = inventory if inventory is not None else scenario.get("stock", [])
        self.stock = StockList()
        if isinstance(raw_stock, dict):
            for k, count in raw_stock.items():
                for _ in range(int(count)):
                    iid = ids.new("I")
                    self.stock.append({"id": iid, "kind": k, "fresh": 100.0})
        elif isinstance(raw_stock, list):
            for it in raw_stock:
                if isinstance(it, dict):
                    iid = it.get("id")
                    if iid:
                        ids.reserve(iid)
                    else:
                        iid = ids.new("I")
                    self.stock.append({"id": iid, "kind": it["kind"], "fresh": float(it.get("fresh", 100.0))})
                elif isinstance(it, str):
                    iid = ids.new("I")
                    self.stock.append({"id": iid, "kind": it, "fresh": 100.0})

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
        self.menu_ids = [d for d in (scenario.get("menu_ids") or sorted(self.menu)) if d in self.menu]
        self.tip_rate = float(t["tip_rate"])
        self.tip_min_ratio = float(t["tip_min_patience_ratio"])
        self.tip_reputation = float(t["tip_reputation"])
        self.steps = 0
        self.served = 0
        self.left = 0
        self.tips = 0

        self.customers = []
        for c in scenario.get("customers", []):
            cust = dict(c)
            dish = cust.get("dish_id")
            cust.setdefault("state", "waiting")
            cust.setdefault("order_tick", 0)
            order_id = cust.get("order_id") or cust.get("id")
            cust.setdefault("order_id", order_id)
            cust.setdefault("order_status", "reserved")
            cust.setdefault("patience_ticks_left", self.patience_ticks)
            cust.setdefault("patience_max", self.patience_ticks)
            res = cust.get("reserved")
            if isinstance(res, dict):
                res_ids = []
                for k, n in res.items():
                    avail = [it for it in self.stock if it["kind"] == k and it["id"] not in res_ids]
                    res_ids.extend([it["id"] for it in avail[:n]])
                cust["reserved"] = res_ids
            elif res is None:
                if dish in self.menu:
                    recipe = self.menu[dish].get("recipe", {})
                    res_ids = []
                    for k, n in recipe.items():
                        avail = [it for it in self.stock if it["kind"] == k and it["id"] not in res_ids]
                        res_ids.extend([it["id"] for it in avail[:n]])
                    if len(res_ids) == sum(recipe.values()):
                        cust["reserved"] = res_ids
                        cust["order_status"] = "reserved"
                    else:
                        cust["reserved"] = []
                        cust["order_status"] = "unfulfillable"
                else:
                    cust["reserved"] = []
            else:
                cust["reserved"] = list(res)
            for iid in cust["reserved"]:
                self.ids.reserve(iid)
            price = int(self.menu.get(dish, {}).get("price", 0))
            cust.setdefault("price", price)
            cust.setdefault("base_price", price)
            cust.setdefault("tip", 0)
            cust.setdefault("stove_id", None)
            cust.setdefault("eat_ticks_left", self.eat_ticks)
            self.customers.append(cust)
            self.ids.reserve(cust["id"])
            if cust.get("order_id"):
                self.ids.reserve(cust["order_id"])

        for st in self.stoves:
            if st.get("order_id"):
                self.ids.reserve(st["order_id"])
        self.money = int(scenario.get("money", 0))
        self.earned = int(scenario.get("earned", self.money))
        self.shift_earned = 0
        self.done = False
        self.reason = None

    @property
    def reserved(self):
        res_ids = set()
        for c in self.customers:
            if c.get("state") == "waiting" and c.get("order_status") == "reserved":
                res_ids.update(c.get("reserved") or [])
        counts = {}
        for it in self.stock:
            if it["id"] in res_ids:
                counts[it["kind"]] = counts.get(it["kind"], 0) + 1
        return counts

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
            "stock": sort_by_id([dict(it) for it in self.stock]),
            "hand": self.hand,
            "stoves": [{k: s.get(k) for k in ("id", "pos", "state", "dish", "order_id",
                                              "cook_ticks_left", "ready_ticks")} for s in self.stoves],
            "tables": [{"id": tb["id"], "pos": tb["pos"], "customer_id": occupied.get(tb["id"])}
                       for tb in self.tables],
            "customers": sort_by_id([dict(c) for c in self.customers]),
            "served": self.served, "left": self.left,
        }

    # --- kho / giữ chỗ theo ID cá thể ------------------------------------------
    def _can_cook(self, dish_id) -> bool:
        recipe = self.menu.get(dish_id, {}).get("recipe", {})
        if not recipe:
            return False
        reserved_ids = set()
        for c in self.customers:
            if c.get("state") == "waiting" and c.get("order_status") == "reserved":
                reserved_ids.update(c.get("reserved") or [])
        chosen_ids = set()
        for kind, n in recipe.items():
            avail_count = sum(1 for it in self.stock
                              if it["kind"] == kind and it["fresh"] >= self.spoiled_below
                              and it["id"] not in reserved_ids and it["id"] not in chosen_ids)
            if avail_count < int(n):
                return False
            for it in self.stock:
                if (it["kind"] == kind and it["fresh"] >= self.spoiled_below
                        and it["id"] not in reserved_ids and it["id"] not in chosen_ids):
                    chosen_ids.add(it["id"])
                    if len(chosen_ids) >= int(n):
                        break
        return True

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
            return
        dish = self._pick_dish()
        if dish is None:
            events.append(("no_dish", {}))
            return

        recipe = dict(self.menu[dish]["recipe"])
        reserved_ids = set()
        for other_c in self.customers:
            if other_c.get("state") == "waiting" and other_c.get("order_status") == "reserved":
                reserved_ids.update(other_c.get("reserved") or [])
        chosen_ids = []
        for kind, n in recipe.items():
            avail = [it for it in self.stock
                     if it["kind"] == kind and it["fresh"] >= self.spoiled_below
                     and it["id"] not in reserved_ids and it["id"] not in chosen_ids]
            avail.sort(key=lambda it: (-it["fresh"], id_key(it["id"])))
            chosen_ids.extend([it["id"] for it in avail[:n]])

        cid = self.ids.new("C")
        cust = {
            "id": cid,
            "table_id": table["id"],
            "dish_id": dish,
            "state": "waiting",
            "order_tick": self.steps,
            "order_id": cid,
            "order_status": "reserved",
            "patience_ticks_left": self.patience_ticks,
            "patience_max": self.patience_ticks,
            "reserved": chosen_ids,
            "price": int(self.menu[dish]["price"]),
            "base_price": int(self.menu[dish]["price"]),
            "tip": 0,
            "stove_id": None,
            "eat_ticks_left": self.eat_ticks
        }
        self.customers.append(cust)
        events.append(("customer_arrived", {
            "customer_id": cid,
            "order_id": cid,
            "table_id": table["id"],
            "dish_id": dish,
        }))

    def _clamp_rep(self, value):
        lo = float(self.t.get("reputation_min", 0))
        hi = float(self.t.get("reputation_max", 5))
        return min(hi, max(lo, value))

    def _customer_left(self, cust, events, reason="patience"):
        self.customers.remove(cust)
        cust["reserved"] = []
        self.left += 1
        if reason == "patience":
            self.reputation = self._clamp_rep(self.reputation + float(self.t.get("left_reputation_delta", 0.0)))
        events.append(("customer_left", {
            "customer_id": cust["id"],
            "table_id": cust["table_id"],
            "order_id": cust.get("order_id"),
            "reason": reason
        }))

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
                  if c.get("state") == "waiting" and c.get("order_status") == "reserved" and c.get("reserved")]
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
                self.hand = {
                    "dish_id": st["dish"],
                    "order_id": st["order_id"],
                    "base_price": st.get("base_price")
                }
                cust = self._customer_by_order(st["order_id"])
                if cust is not None:
                    cust["order_status"] = "picked"
                events.append(("dish_picked", {
                    "stove_id": st["id"],
                    "dish_id": st["dish"],
                    "order_id": st["order_id"]
                }))
                st.update(state="idle", dish=None, order_id=None, base_price=None, cook_ticks_left=0, ready_ticks=0)
            return
        if st["state"] != "idle":
            return
        order = self._oldest_order()
        if order is None:
            return
        dish = order["dish_id"]

        # Tiêu đúng các id đang giữ từ stock
        res_set = set(order.get("reserved") or [])
        used_items = [it for it in self.stock if it["id"] in res_set]
        self.stock = StockList(it for it in self.stock if it["id"] not in res_set)

        used_items_sorted = sorted(used_items, key=lambda it: (it["kind"], id_key(it["id"])))

        avg_fresh = (sum(it["fresh"] for it in used_items) / len(used_items)) if used_items else 100.0
        listed_price = int(self.menu[dish]["price"])
        base_price = int(math.floor(listed_price * avg_fresh / 100.0))

        if self.flood.get("active"):
            linh_items = [it for it in used_items if it["kind"] == "ca_linh"]
            if linh_items:
                avg_linh_fresh = sum(it["fresh"] for it in linh_items) / len(linh_items)
                if avg_linh_fresh >= float(self.flood.get("bonus_fresh_threshold", 80.0)):
                    bonus_ratio = float(self.flood.get("bonus_ratio", 0.1))
                    base_price = int(math.floor(base_price * (1.0 + bonus_ratio)))

        order["base_price"] = base_price
        order["order_status"] = "cooking"
        order["stove_id"] = st["id"]
        order["reserved"] = []

        st.update(
            state="cooking",
            dish=dish,
            order_id=order["order_id"],
            base_price=base_price,
            cook_ticks_left=int(round(self.menu[dish]["cook_s"] * TICK)),
            ready_ticks=0
        )
        events.append(("cook_started", {
            "stove_id": st["id"],
            "order_id": order["order_id"],
            "dish_id": dish,
            "table_id": order["table_id"],
            "items": used_items_sorted,
            "base_price": base_price
        }))

    def _use_table(self, tb, events):
        cust = self._customer_at(tb["id"])
        if cust is None or cust.get("state") != "waiting" or not isinstance(self.hand, dict):
            return
        if self.hand.get("dish_id") != cust.get("dish_id"):
            return
        if self.hand.get("order_id") is not None and self.hand.get("order_id") != cust.get("order_id"):
            return
        base_price = self.hand.get("base_price")
        if base_price is None:
            base_price = cust.get("base_price", self.menu[cust["dish_id"]]["price"])
        cust["base_price"] = base_price
        pmax = int(cust.get("patience_max") or self.patience_ticks)
        ratio = int(cust.get("patience_ticks_left", 0)) / float(pmax)
        tip = int(math.floor(base_price * self.tip_rate)) if ratio >= self.tip_min_ratio else 0
        self.hand = None
        cust["state"] = "eating"
        cust["eat_ticks_left"] = self.eat_ticks
        cust["tip"] = tip
        cust["order_status"] = "served"
        events.append(("served", {
            "table_id": tb["id"],
            "customer_id": cust["id"],
            "dish_id": cust["dish_id"],
            "order_id": cust["order_id"],
            "tip": tip
        }))

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
                    events.append(("dish_ready", {
                        "stove_id": st["id"],
                        "dish_id": st["dish"],
                        "order_id": st.get("order_id")
                    }))
            elif st["state"] == "ready":
                st["ready_ticks"] = int(st.get("ready_ticks", 0)) + 1

    def _tick_eating(self, events):
        for c in sort_by_id([c for c in self.customers if c.get("state") == "eating"]):
            c["eat_ticks_left"] = max(0, int(c.get("eat_ticks_left", 0)) - 1)
            if c["eat_ticks_left"] == 0:
                self._pay(c, events, reason="finished_eating")

    def _pay(self, cust, events, reason="finished_eating"):
        price = int(cust.get("base_price", cust.get("price", 0)))
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
        events.append(("paid", {
            "customer_id": cust["id"],
            "table_id": cust["table_id"],
            "dish_id": cust.get("dish_id"),
            "price": price,
            "tip": tip,
            "amount": total,
            "reason": reason,
            "money": self.money
        }))

    def _close_shift(self, events):
        for c in sort_by_id([c for c in self.customers if c.get("state") == "eating"]):
            self._pay(c, events, reason="closing")
        for c in sort_by_id(list(self.customers)):
            self._customer_left(c, events, reason="closing")
        for st in self.stoves:
            st.update(state="idle", dish=None, order_id=None, base_price=None, cook_ticks_left=0, ready_ticks=0)
        self.hand = None

    def _quan_end(self, events):
        events.append(("quan_end", {
            "reason": "time", "money": self.money, "earned": self.earned,
            "shift_earned": self.shift_earned, "reputation": self.reputation,
            "served": self.served, "left": self.left, "tips": self.tips
        }))

    def step(self, inp):
        events = []
        self.steps += 1
        self.time_left_ticks = max(0, self.time_left_ticks - 1)

        # 1. Hao tươi kho thô, phát spoiled theo id
        newly_spoiled = []
        for it in self.stock:
            old_fresh = it["fresh"]
            new_fresh = max(0.0, round(old_fresh - self.decay_per_tick, 3))
            it["fresh"] = new_fresh
            if old_fresh >= self.spoiled_below and new_fresh < self.spoiled_below:
                newly_spoiled.append(it)

        if newly_spoiled:
            for it in sort_by_id(newly_spoiled):
                events.append(("spoiled", {
                    "item_id": it["id"],
                    "kind": it["kind"],
                    "location": "stock"
                }))

            # Xử lý giữ chỗ bị ươn: nếu phần giữ có cá thể vừa ươn, nhả toàn bộ phần giữ và thử giữ lại đúng một lần
            spoiled_ids = {it["id"] for it in newly_spoiled}
            affected = [c for c in self.customers
                        if c.get("state") == "waiting" and c.get("order_status") == "reserved"
                        and any(iid in spoiled_ids for iid in (c.get("reserved") or []))]
            affected.sort(key=lambda c: (int(c.get("order_tick", 0)), id_key(c["table_id"])))
            for c in affected:
                c["reserved"] = []
                dish_id = c["dish_id"]
                recipe = self.menu[dish_id]["recipe"]
                other_reserved = set()
                for oc in self.customers:
                    if oc is not c and oc.get("state") == "waiting" and oc.get("order_status") == "reserved":
                        other_reserved.update(oc.get("reserved") or [])
                can_re_reserve = True
                new_reserved = []
                for kind, n in recipe.items():
                    avail = [it for it in self.stock
                             if it["kind"] == kind and it["fresh"] >= self.spoiled_below
                             and it["id"] not in other_reserved and it["id"] not in new_reserved]
                    if len(avail) < n:
                        can_re_reserve = False
                        break
                    avail.sort(key=lambda it: (-it["fresh"], id_key(it["id"])))
                    new_reserved.extend([it["id"] for it in avail[:n]])
                if can_re_reserve:
                    c["reserved"] = new_reserved
                else:
                    c["order_status"] = "unfulfillable"

        # 2. Bếp nấu
        self._tick_stoves(events)

        # 3. Khách ăn
        self._tick_eating(events)

        # 4. Kiên nhẫn khách đợi
        for c in sort_by_id(self.customers):
            if c.get("state") == "waiting" and int(c.get("order_tick", 0)) < self.steps:
                c["patience_ticks_left"] = max(0, int(c.get("patience_ticks_left", 0)) - 1)

        # 5. Di chuyển & tương tác
        self._move(inp)
        if inp.pressed("interact"):
            kind, target = self._interact_target()
            if kind == "stove":
                self._use_stove(target, events)
            elif kind == "table":
                self._use_table(target, events)

        # 6. Kiểm tra kiên nhẫn hết hạn / khách mới / đóng ca
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
