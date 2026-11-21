"""Chế độ `day`: mỗi Ngày = DayIntro -> gather -> quan -> Shop, lặp tới `days`.

- Tiền/earned/uy tín/cấp nâng cấp giữ qua Ngày; cấp đã mua chỉ áp dụng từ Ngày kế.
- pause: chỉ tăng tick ngoài; sim_tick/phase_tick/lịch/timer đứng yên.
"""

import copy

from .sim.gather import GatherSim
from .sim.quan import QuanSim


class ShopSim:
    mode = "shop"
    phase = "shop"

    def __init__(self, tuning, state):
        self.t = tuning["shop"]
        self.money = int(state.get("money", 0))
        self.earned = int(state.get("earned", 0))
        self.upgrades = dict(state.get("upgrades", {}))
        self.active = dict(state.get("active_upgrades", {}))
        self.stock = dict(state.get("stock", {}))
        self.time_left_ticks = int(self.t.get("max_ticks", 600))
        self.reputation = float(state.get("reputation", tuning["quan"]["reputation_initial"]))
        self.done = False
        self.reason = None
        self.steps = 0

    def snapshot(self) -> dict:
        return {"stock": {k: self.stock[k] for k in sorted(self.stock) if self.stock[k] > 0},
                "time_left_ticks": self.time_left_ticks,
                "upgrades": dict(self.upgrades), "active_upgrades": dict(self.active)}

    def step(self, inp):
        events = []
        self.steps += 1
        self.time_left_ticks = max(0, self.time_left_ticks - 1)
        buy = getattr(inp, "buy", None)
        if buy:
            self._buy(buy, events)
        if inp.pressed("shop_done"):
            return self._close(events, "done")
        if self.time_left_ticks <= 0:
            return self._close(events, "time")
        return events

    def _buy(self, action, events):
        if action not in ("oxygen", "hp"):
            events.append(("buy_failed", {"action": action, "reason": "unknown"}))
            return
        tiers = self.t.get("upgrades", {}).get(action, [])
        level = int(self.upgrades.get(action, 0))
        if level >= len(tiers):
            events.append(("buy_failed", {"action": action, "reason": "max_level"}))
            return
        item = tiers[level]
        price = int(item["price"])
        if self.money < price:
            events.append(("buy_failed", {"action": action, "reason": "funds"}))
            return
        self.money -= price
        self.upgrades[action] = level + 1
        events.append(("bought", {"upgrade": action, "level": level + 1, "price": price, "money": self.money}))

    def _close(self, events, reason):
        self.done = True
        self.reason = reason
        events.append(("shop_end", {"reason": reason}))
        return events


class DaySim:
    mode = "day"

    def __init__(self, tuning, scenario, streams, ids, days=1):
        self.tuning = tuning
        self.scenario = scenario or {}
        self.rng = streams
        self.ids = ids
        self.days_target = max(1, int(days))
        block = self.scenario.get("day", {})
        self._money = int(block.get("money", 0))
        self._earned = int(block.get("earned", 0))
        self._reputation = float(block.get("reputation", tuning["quan"]["reputation_initial"]))
        self.upgrades = dict(block.get("upgrades", {}))
        self.active_upgrades = dict(self.upgrades)
        self.plan = block.get("day_plan") or tuning.get("day_plan", [])
        self.day = 1
        self.days_completed = 0
        self.phase = "gather"
        self.phase_tick = 0
        self.steps = 0
        self.paused = False
        self.done = False
        self.reason = None
        self._buffer = []
        self._start_day(1)

    # --- trạng thái chung cho runner -----------------------------------------
    @property
    def money(self):
        if self.phase == "quan":
            return self.quan.money
        if self.phase == "shop":
            return self.shop.money
        return self._money

    @property
    def earned(self):
        if self.phase == "quan":
            return self.quan.earned
        if self.phase == "shop":
            return self.shop.earned
        return self._earned

    @property
    def reputation(self):
        if self.phase == "quan":
            return self.quan.reputation
        return self._reputation

    @property
    def time_left_ticks(self):
        if self.phase == "quan":
            return self.quan.time_left_ticks
        if self.phase == "shop":
            return self.shop.time_left_ticks
        return self.gather.time_left_ticks

    # --- dựng Ngày ------------------------------------------------------------
    def _plan_for(self, day):
        for item in self.plan:
            if int(item.get("day", 0)) == day:
                return item
        return {"day": day, "dishes": {}, "ingredients": {}}

    def _ingredients(self, plan):
        out = {}
        for dish, count in (plan.get("dishes") or {}).items():
            for kind, need in self.tuning["menu"].get(dish, {}).get("recipe", {}).items():
                out[kind] = out.get(kind, 0) + int(need) * int(count)
        return {k: out[k] for k in sorted(out)}

    def _gather_tuning(self):
        tuning = copy.deepcopy(self.tuning)
        g = tuning["gather"]
        shop_up = tuning.get("shop", {}).get("upgrades", {})
        oxy = int(self.active_upgrades.get("oxygen", 0))
        hp = int(self.active_upgrades.get("hp", 0))
        if oxy > 0 and oxy <= len(shop_up.get("oxygen", [])):
            g["oxygen_max_s"] = shop_up["oxygen"][oxy - 1]["oxygen_max_s"]
        if hp > 0 and hp <= len(shop_up.get("hp", [])):
            g["hp_max"] = shop_up["hp"][hp - 1]["hp_max"]
        return tuning

    def _start_day(self, day):
        self.day = day
        self.phase_tick = 0
        self.paused = False
        plan = self._plan_for(day)
        self.day_plan = {"dishes": dict(plan.get("dishes") or {}),
                         "ingredients": self._ingredients(plan)}
        gsc = dict(self.scenario.get("gather") or {})
        gsc.pop("hold", None)
        gsc.pop("time_left_ticks", None)
        gsc["day"] = day
        self.gather = GatherSim(self._gather_tuning(), gsc, self.rng, self.ids, day=day)
        self.phase = "gather"
        self._buffer += [("day_start", {}, "gather", day),
                         ("day_plan", {"dishes": dict(self.day_plan["dishes"]),
                                       "ingredients": dict(self.day_plan["ingredients"])}, "gather", day),
                         ("phase_start", {}, "gather", day)]

    def _to_quan(self, events):
        stock = self.gather.inventory_items()
        qsc = dict(self.scenario.get("quan") or {})
        qsc["stock"] = stock
        qsc["reputation"] = self.reputation
        qsc["money"] = self._money
        qsc["earned"] = self._earned
        qsc["menu_ids"] = [d for d in self.day_plan["dishes"] if d in self.tuning["menu"]]
        self.quan = QuanSim(self.tuning, qsc, self.rng, self.ids)
        self.phase = "quan"
        self.phase_tick = 0
        events.append(("phase_start", {}, "quan", self.day))

    def _to_shop(self, events):
        self._money = int(self.quan.money)
        self._earned = int(self.quan.earned)
        self._reputation = float(self.quan.reputation)
        self.shop = ShopSim(self.tuning, {"money": self._money, "earned": self._earned,
                                          "upgrades": self.upgrades, "active_upgrades": self.active_upgrades,
                                          "stock": dict(self.quan.stock), "reputation": self._reputation})
        self.phase = "shop"
        self.phase_tick = 0
        events.append(("phase_start", {}, "shop", self.day))

    def _finish_shop(self, events):
        self._money = self.shop.money
        self._earned = max(self._earned, self.shop.earned)
        self.upgrades = dict(self.shop.upgrades)
        self.days_completed += 1
        if self.days_completed >= self.days_target:
            self.done = True
            self.reason = "days_complete"
            return
        self.active_upgrades = dict(self.upgrades)
        self._start_day(self.day + 1)
        events += self._buffer
        self._buffer = []

    # --- vòng chạy ------------------------------------------------------------
    def step(self, inp):
        events = list(self._buffer)
        self._buffer = []
        day_now = self.day
        if self.paused:
            if inp.pressed("pause"):
                self.paused = False
                events.append(("resumed", {}, self.phase, self.day))
            else:
                return events
        elif inp.pressed("pause"):
            self.paused = True
            events.append(("paused", {}, self.phase, self.day))
            return events
        self.steps += 1
        self.phase_tick += 1
        if self.phase == "gather":
            events += [(n, d, "gather", day_now) for n, d in self.gather.step(inp)]
            if self.gather.done:
                self._to_quan(events)
        elif self.phase == "quan":
            events += [(n, d, "quan", day_now) for n, d in self.quan.step(inp)]
            if self.quan.done:
                self._to_shop(events)
        else:
            events += [(n, d, "shop", day_now) for n, d in self.shop.step(inp)]
            if self.shop.done:
                self._finish_shop(events)
        return events

    def snapshot(self) -> dict:
        base = {"day": self.day, "day_plan": self.day_plan, "upgrades": dict(self.upgrades),
                "active_upgrades": dict(self.active_upgrades), "days_completed": self.days_completed}
        if self.phase == "quan":
            base.update(self.quan.snapshot())
        elif self.phase == "shop":
            base.update(self.shop.snapshot())
        else:
            base.update(self.gather.snapshot())
        base["state"] = "paused" if self.paused else ("finished" if self.done else "playing")
        return base