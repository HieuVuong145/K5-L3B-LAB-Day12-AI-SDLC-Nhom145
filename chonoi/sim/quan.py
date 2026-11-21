"""Buổi tối — Mở Quán. KHUNG: đi lại, chặn biên, đồng hồ, kho nạp từ file/scenario.

Đã làm (lát 3 & lát 4, PRD mục F):
  - Khách đến theo lịch (first_customer_tick, customer_interval_s*60)
  - Chọn món theo seed trong các món đủ nguyên liệu khả dụng (stock - reserved); không có món -> no_dish
  - Giữ nguyên liệu ngay khi khách vào, kiên nhẫn giảm từ bước sau
  - Tối đa 1 interact:
      * Bếp idle: lấy đơn reserved cũ nhất, tiêu nguyên liệu, chuyển cooking
      * Bếp ready: người chơi nhấc lên tay trống (hand), bếp về idle
      * Bàn có khách: giao món khớp order_id, khách eating, tính boa
  - Khách ăn xong trả tiền, boa, tăng uy tín (finished_eating)
  - Khách hết kiên nhẫn khi ca còn giờ -> rời bàn, trừ uy tín, nhả giữ chỗ / hủy món
  - Hết ca: khách ăn thanh toán ngay, khách chờ rời không trừ uy tín (closing) -> quan_end
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
        # kho: --inventory HOẶC scenario.stock (cả hai -> cli đã báo mã 2)
        self.stock = dict(inventory if inventory is not None else scenario.get("stock", {}))
        self.hand = scenario.get("hand")
        self.time_left_ticks = scenario.get("time_left_ticks", int(round(t["duration_s"] * 60)))
        self.reputation = scenario.get("reputation", t["reputation_initial"])
        self.stoves = [dict(s, state=s.get("state", "idle"), dish=s.get("dish"),
                            cook_ticks_left=s.get("cook_ticks_left", 0), ready_ticks=s.get("ready_ticks", 0))
                       for s in self._merge(t["stoves"], scenario.get("stoves", []))]
        self.tables = self._merge(t["tables"], scenario.get("tables", []))
        self.patience_ticks = int(round(t["patience_s"] * TICK))
        self.eat_ticks = int(round(t["eat_s"] * TICK))
        self.spawn_every = max(1, int(round(t["customer_interval_s"] * TICK)))
        self.first_customer_tick = int(t["first_customer_tick"])
        self.random_customers = bool(scenario.get("random_customers", True))
        self.steps = 0          # số bước đã chạy = tick hiện tại của pha
        self.served = 0         # số khách đã phục vụ
        self.left = 0           # số khách bỏ đi vì hết kiên nhẫn
        self.reserved = {}      # kind -> số đang giữ cho các đơn reserved
        self.customers = []
        for c in scenario.get("customers", []):
            cust = dict(c)
            cust.setdefault("state", "waiting")
            cust.setdefault("dish_id", None)
            cust.setdefault("order_tick", 0)
            cust.setdefault("order_id", cust.get("id"))
            cust.setdefault("patience_ticks_left", self.patience_ticks)
            cust.setdefault("eat_ticks_left", self.eat_ticks)
            dish_id = cust["dish_id"]
            if dish_id and dish_id in self.menu:
                cust.setdefault("base_price", int(self.menu[dish_id]["price"]))
                cust.setdefault("reserved", dict(self.menu[dish_id].get("recipe", {})))
            else:
                cust.setdefault("base_price", None)
                cust.setdefault("reserved", {})
            cust.setdefault("tip", None)
            cust.setdefault("order_status", "reserved" if cust["reserved"] else "assigned")
            self.customers.append(cust)
            self.ids.reserve(cust["id"])
            self._add_reserved(cust.get("reserved") or {})
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

    # --- khách (lát 3 & 4) --------------------------------------------------------
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
        options = [d for d in sorted(self.menu) if self._can_cook(d)]
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
        cid = self.ids.new("C")
        cust = {"id": cid, "table_id": table["id"], "dish_id": dish,
                "state": "waiting", "order_tick": self.steps, "order_id": cid,
                "patience_ticks_left": self.patience_ticks, "eat_ticks_left": self.eat_ticks,
                "reserved": recipe, "base_price": int(self.menu[dish]["price"]), "tip": None, "order_status": "reserved"}
        self.customers.append(cust)
        self._add_reserved(recipe)
        events.append(("customer_arrived", {"order_id": cid, "table_id": table["id"], "dish_id": dish}))

    def _customer_left(self, cust, reason, events):
        self.customers.remove(cust)
        self._release(cust.get("reserved") or {})
        if self.hand and self.hand.get("order_id") == cust["id"]:
            self.hand = None
        for s in self.stoves:
            if s.get("dish") and s["dish"].get("order_id") == cust["id"]:
                s["state"] = "idle"
                s["dish"] = None
                s["cook_ticks_left"] = 0
                s["ready_ticks"] = 0
        if reason == "patience":
            self.left += 1
            lo = float(self.t.get("reputation_min", 0))
            hi = float(self.t.get("reputation_max", 5))
            self.reputation = min(hi, max(lo, round(self.reputation + float(self.t.get("left_reputation_delta", 0.0)), 3)))
        events.append(("customer_left", {
            "order_id": cust["id"],
            "table_id": cust["table_id"],
            "reason": reason,
            "reputation": self.reputation,
        }))

    def snapshot(self) -> dict:
        occupied = {c["table_id"]: c["id"] for c in self.customers}
        return {
            "player": {"pos": self.pos},
            "stock": {k: self.stock[k] for k in sorted(self.stock) if self.stock[k] > 0},
            "hand": self.hand,
            "stoves": [{k: s.get(k) for k in ("id", "pos", "state", "dish", "cook_ticks_left", "ready_ticks")}
                       for s in self.stoves],
            "tables": [{"id": tb["id"], "pos": tb["pos"], "customer_id": occupied.get(tb["id"])} for tb in self.tables],
            "customers": [{
                "id": c["id"],
                "table_id": c["table_id"],
                "dish_id": c["dish_id"],
                "order_tick": c.get("order_tick", 0),
                "state": c.get("state", "waiting"),
                "patience_ticks_left": c.get("patience_ticks_left", 0),
                "eat_ticks_left": c.get("eat_ticks_left", 0),
                "order_status": c.get("order_status", "reserved"),
                "reserved": {k: c["reserved"][k] for k in sorted(c.get("reserved", {})) if c["reserved"][k] > 0},
                "base_price": c.get("base_price"),
                "tip": c.get("tip"),
            } for c in sort_by_id(self.customers)],
        }

    def step(self, inp):
        events = []
        self.steps += 1
        self.time_left_ticks = max(0, self.time_left_ticks - 1)

        # 1. Tăng ready_ticks cho món đã ready ở đầu bước
        for s in self.stoves:
            if s.get("state") == "ready":
                s["ready_ticks"] = s.get("ready_ticks", 0) + 1

        # 2. Bếp cooking đếm ngược, chuyển ready
        for s in sort_by_id(self.stoves):
            if s.get("state") == "cooking":
                s["cook_ticks_left"] = max(0, s.get("cook_ticks_left", 0) - 1)
                if s["cook_ticks_left"] == 0:
                    s["state"] = "ready"
                    s["ready_ticks"] = 0
                    events.append(("dish_ready", {
                        "stove_id": s["id"],
                        "order_id": s["dish"]["order_id"],
                        "dish_id": s["dish"]["dish_id"],
                    }))

        # 3. Khách eating & waiting đếm ngược
        for c in sort_by_id(self.customers):
            if c.get("state") == "eating":
                c["eat_ticks_left"] = max(0, int(c.get("eat_ticks_left", 0)) - 1)
            elif c.get("state") == "waiting":
                if int(c.get("order_tick", 0)) < self.steps:
                    c["patience_ticks_left"] = max(0, int(c.get("patience_ticks_left", 0)) - 1)

        # 4. Di chuyển
        self._move(inp)

        # 5. Tối đa một interact
        if inp.pressed("interact"):
            r = float(self.t["interact_radius"])
            candidates = []
            for s in self.stoves:
                dist = math.dist(self.pos, s["pos"])
                if dist <= r:
                    candidates.append((dist, 0, id_key(s["id"]), s, "stove"))
            for tb in self.tables:
                dist = math.dist(self.pos, tb["pos"])
                if dist <= r:
                    candidates.append((dist, 1, id_key(tb["id"]), tb, "table"))
            if candidates:
                candidates.sort(key=lambda x: (x[0], x[1], x[2]))
                _, _, _, target, target_type = candidates[0]
                if target_type == "stove":
                    if target["state"] == "idle":
                        reserved_custs = [c for c in self.customers if c.get("state") == "waiting" and (c.get("reserved") or c.get("order_status") == "reserved")]
                        if reserved_custs:
                            reserved_custs.sort(key=lambda c: (int(c.get("order_tick", 0)), id_key(c["table_id"])))
                            chosen_c = reserved_custs[0]
                            dish_id = chosen_c["dish_id"]
                            recipe = self.menu[dish_id]["recipe"]
                            for kind, amt in recipe.items():
                                self.stock[kind] = self.stock.get(kind, 0) - int(amt)
                                self.reserved[kind] = max(0, self.reserved.get(kind, 0) - int(amt))
                            recipe_items = []
                            for kind in sorted(recipe.keys()):
                                recipe_items.extend([kind] * int(recipe[kind]))
                            base_price = int(self.menu[dish_id]["price"])
                            chosen_c["order_status"] = "assigned"
                            chosen_c["reserved"] = {}
                            chosen_c["base_price"] = base_price
                            target["state"] = "cooking"
                            target["cook_ticks_left"] = int(round(self.menu[dish_id]["cook_s"] * TICK))
                            target["ready_ticks"] = 0
                            target["dish"] = {
                                "order_id": chosen_c["id"],
                                "dish_id": dish_id,
                                "base_price": base_price,
                            }
                            events.append(("cook_started", {
                                "stove_id": target["id"],
                                "order_id": chosen_c["id"],
                                "dish_id": dish_id,
                                "items": recipe_items,
                                "base_price": base_price,
                            }))
                    elif target["state"] == "ready":
                        if self.hand is None:
                            self.hand = dict(target["dish"])
                            dish_info = target["dish"]
                            target["state"] = "idle"
                            target["dish"] = None
                            target["cook_ticks_left"] = 0
                            target["ready_ticks"] = 0
                            events.append(("dish_picked", {
                                "stove_id": target["id"],
                                "order_id": dish_info["order_id"],
                                "dish_id": dish_info["dish_id"],
                            }))
                elif target_type == "table":
                    table_cust = next((c for c in self.customers if c["table_id"] == target["id"]), None)
                    if table_cust and table_cust.get("state") == "waiting" and self.hand is not None:
                        if self.hand["order_id"] == table_cust["id"]:
                            dish_payload = self.hand
                            self.hand = None
                            table_cust["state"] = "eating"
                            table_cust["eat_ticks_left"] = int(round(self.t["eat_s"] * TICK))
                            table_cust["order_status"] = "served"
                            base_price = dish_payload["base_price"]
                            table_cust["base_price"] = base_price
                            p_ratio = table_cust.get("patience_ticks_left", 0) / float(self.patience_ticks)
                            if p_ratio >= float(self.t["tip_min_patience_ratio"]):
                                tip = int(math.floor(base_price * float(self.t["tip_rate"])))
                            else:
                                tip = 0
                            table_cust["tip"] = tip
                            events.append(("served", {
                                "order_id": table_cust["id"],
                                "table_id": target["id"],
                                "dish_id": table_cust["dish_id"],
                                "patience_ticks_left": table_cust["patience_ticks_left"],
                                "base_price": base_price,
                                "tip": tip,
                            }))

        # 6. Khách ăn xong / kiên nhẫn hết / đóng ca theo thứ tự bàn
        if self.time_left_ticks > 0:
            for tb in sort_by_id(self.tables):
                c = next((cust for cust in self.customers if cust["table_id"] == tb["id"]), None)
                if not c:
                    continue
                if c.get("state") == "eating" and int(c.get("eat_ticks_left", 0)) <= 0:
                    amount = int(c["base_price"]) + int(c.get("tip") or 0)
                    self.money += amount
                    self.earned += amount
                    self.shift_earned += amount
                    self.served += 1
                    if int(c.get("tip") or 0) > 0:
                        lo = float(self.t.get("reputation_min", 0))
                        hi = float(self.t.get("reputation_max", 5))
                        self.reputation = min(hi, max(lo, round(self.reputation + float(self.t.get("tip_reputation", 0)), 3)))
                    events.append(("paid", {
                        "order_id": c["id"],
                        "table_id": tb["id"],
                        "base_price": c["base_price"],
                        "tip": c.get("tip") or 0,
                        "amount": amount,
                        "reason": "finished_eating",
                    }))
                    self.customers.remove(c)
                elif c.get("state") == "waiting" and int(c.get("patience_ticks_left", 0)) <= 0:
                    self._customer_left(c, "patience", events)

            # 7. Khách mới theo lịch (chỉ khi ca còn giờ)
            self._maybe_spawn(events)

        else:
            # Hết ca (time_left_ticks <= 0)
            for tb in sort_by_id(self.tables):
                c = next((cust for cust in self.customers if cust["table_id"] == tb["id"]), None)
                if not c:
                    continue
                if c.get("state") == "eating":
                    amount = int(c["base_price"]) + int(c.get("tip") or 0)
                    self.money += amount
                    self.earned += amount
                    self.shift_earned += amount
                    self.served += 1
                    if int(c.get("tip") or 0) > 0:
                        lo = float(self.t.get("reputation_min", 0))
                        hi = float(self.t.get("reputation_max", 5))
                        self.reputation = min(hi, max(lo, round(self.reputation + float(self.t.get("tip_reputation", 0)), 3)))
                    events.append(("paid", {
                        "order_id": c["id"],
                        "table_id": tb["id"],
                        "base_price": c["base_price"],
                        "tip": c.get("tip") or 0,
                        "amount": amount,
                        "reason": "closing",
                    }))
                    self.customers.remove(c)
                elif c.get("state") == "waiting":
                    self._customer_left(c, "closing", events)

            self.done = True
            self.reason = "time"
            events.append(("quan_end", {
                "reason": "time",
                "money": self.money,
                "earned": self.earned,
                "shift_earned": self.shift_earned,
                "reputation": self.reputation,
            }))

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
