"""Buổi tối — Mở Quán. KHUNG: đi lại, chặn biên, đồng hồ, kho nạp từ file/scenario.

Đã làm (lát 3, PRD mục F): khách đến theo lịch, chọn món nấu được, giữ chỗ nguyên liệu,
  kiên nhẫn, bỏ đi (customer_left), no_dish, vòng đời khách.
  - lịch: tick first_customer_tick, sau đó +customer_interval_s*60; hết bàn thì bỏ lượt
  - chọn đều theo seed trong các món nấu được với kho khả dụng (tồn - đang giữ); không có món -> no_dish
  - vào bàn trống id nhỏ nhất, giữ nguyên liệu ngay, kiên nhẫn đầy và giảm từ bước sau
  - hết kiên nhẫn khi ca còn giờ -> rời bàn, nhả phần giữ, uy tín + left_reputation_delta
Nhóm viết tiếp:
  TODO(nhóm, lát 4): interact tại bếp/bàn (cook_started, dish_ready, dish_picked, served),
                     ăn xong trả tiền (paid), boa, uy tín, đóng ca (quan_end).
"""

from ..ids import sort_by_id
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
        self.served = 0         # lát 4 dùng
        self.left = 0           # số khách bỏ đi vì hết kiên nhẫn
        self.reserved = {}      # kind -> số đang giữ cho các đơn reserved
        self.customers = []
        for c in scenario.get("customers", []):
            cust = dict(c)
            cust.setdefault("state", "waiting")
            cust.setdefault("dish_id", None)
            cust.setdefault("order_tick", 0)
            cust.setdefault("order_id", None)
            cust.setdefault("patience_ticks_left", self.patience_ticks)
            cust.setdefault("reserved", dict(self.menu.get(cust["dish_id"], {}).get("recipe", {})))
            self.customers.append(cust)
            self.ids.reserve(cust["id"])
            if cust.get("order_id"):
                self.ids.reserve(cust["order_id"])
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

    # --- khách (lát 3) -----------------------------------------------------------
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
        cust = {"id": self.ids.new("C"), "table_id": table["id"], "dish_id": dish,
                "state": "waiting", "order_tick": self.steps, "order_id": self.ids.new("O"),
                "patience_ticks_left": self.patience_ticks, "reserved": recipe}
        self.customers.append(cust)
        self._add_reserved(recipe)

    def _customer_left(self, cust, events):
        self.customers.remove(cust)
        self._release(cust.get("reserved") or {})
        self.left += 1
        lo = float(self.t.get("reputation_min", 0))
        hi = float(self.t.get("reputation_max", 5))
        self.reputation = min(hi, max(lo, self.reputation + float(self.t.get("left_reputation_delta", 0.0))))
        events.append(("customer_left", {"customer_id": cust["id"], "table_id": cust["table_id"]}))

    def snapshot(self) -> dict:
        occupied = {c["table_id"]: c["id"] for c in self.customers}
        return {
            "player": {"pos": self.pos},
            "stock": {k: self.stock[k] for k in sorted(self.stock) if self.stock[k] > 0},
            "hand": self.hand,
            "stoves": [{k: s.get(k) for k in ("id", "pos", "state", "dish", "cook_ticks_left", "ready_ticks")}
                       for s in self.stoves],
            "tables": [{"id": tb["id"], "pos": tb["pos"], "customer_id": occupied.get(tb["id"])} for tb in self.tables],
            "customers": sort_by_id(self.customers),
        }

    def step(self, inp):
        events = []
        self.steps += 1
        self.time_left_ticks = max(0, self.time_left_ticks - 1)
        # 1. kiên nhẫn của khách đang chờ (khách vừa vào giữ nguyên ở bước đó, giảm từ bước sau)
        for c in sort_by_id(self.customers):
            if c.get("state") != "waiting" or int(c.get("order_tick", 0)) >= self.steps:
                continue
            c["patience_ticks_left"] = max(0, int(c.get("patience_ticks_left", 0)) - 1)
        if self.time_left_ticks > 0:
            for c in sort_by_id([c for c in self.customers
                                 if c.get("state") == "waiting" and int(c.get("patience_ticks_left", 0)) <= 0]):
                self._customer_left(c, events)
        self._move(inp)
        # TODO(nhóm, lát 4): tối đa MỘT interact, chọn đối tượng theo (khoảng cách, bếp trước bàn, id).
        # 2. khách mới theo lịch: hết bàn thì bỏ lượt, không món nấu được thì no_dish
        if self.time_left_ticks > 0:
            self._maybe_spawn(events)
        if self.time_left_ticks <= 0:
            self.done = True
            self.reason = "time"
            events.append(("quan_end", {"reason": "time", "money": self.money, "earned": self.earned,
                                        "shift_earned": self.shift_earned, "reputation": self.reputation}))
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
