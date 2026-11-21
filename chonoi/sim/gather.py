"""Buổi sáng — Lặn & Hái (`gather`). KHUNG: bơi, chặn mép, đồng hồ, cập bến, xuất kho.

Mặt cắt dòng sông nhìn NGANG: vị trí `[x, d]` (x sang phải, `d` độ sâu hướng xuống, d = 0 là mặt nước).
`move = [x, d]`: thành phần thứ hai DƯƠNG = bơi xuống. Hướng mặt là góc từ +x, dương = xuống.

Đã làm sẵn để smoke test chạy được: bơi + tăng/giảm tốc, chặn mép (d không âm), đồng hồ và hết giờ,
cập bến (`interact` trong vùng bến -> `gather_end` reason `docked`), xuất kho, snapshot đầy đủ trường gather.

Đã làm (lát 1, theo đúng thứ tự một bước trong PRD mục 13.8, "Gather"):
  bơi + oxy + biên + giỏ
      - oxy theo d CUỐI bước: dưới nước (d > surface_depth) trừ 1 tick/tick, mặt nước hồi
        oxygen_refill_per_tick, kẹp [0, oxygen_max_s * 60]
      - đổi vùng đầu/cuối bước -> `dive` / `surface`, data {"pos": [x, d]}
      - oxy từ dương xuống 0 -> `oxygen_empty`, data {"pos": [x, d]} (chỉ một lần)
      - ngạt: oxy = 0 và đang dưới nước -> đếm zero_oxy_ticks, đủ choke_interval_ticks thì -1 Máu
        (`choke`, data {"hp": hp}); lên mặt nước thì zero_oxy_ticks về 0
      - Máu về 0 -> `faint` + gather_end reason `fainted`, mất toàn bộ giỏ (kho rỗng)
      - giỏ: thứ tự nhặt LIFO (mới nhất ở cuối), sức chứa hold_capacity (_add_to_hold/_hold_full)
Nhóm viết tiếp:
  TODO(nhóm, lát 2): hái + bắt cá + cập bến + kho
      - hái nút ở mặt nước (gather, hold_full), nút mọc lại (node_regrown đã có phần đếm ngược)
      - bắt đàn cá bằng `catch` (fish_caught, hold_full, hồi chiêu catch_cd_ticks, chỉ khi dưới nước)
      - cập bến xét TRƯỚC hái (đã có); ghi kho đúng một lần do runner lo
Các tính năng của phase sau chưa nằm trong khung này.
"""

import math

from ..ids import id_key, sort_by_id
from ..inventory import hold_to_items
from .ramp import ramp_velocity

TICK = 60.0
AXES = ("x", "d")


class GatherSim:
    mode = "gather"
    phase = "gather"

    def __init__(self, tuning, scenario, streams, ids, day=1):
        t = tuning["gather"]
        self.t = t
        self.rng = streams
        self.ids = ids
        p = scenario.get("player", {})
        self.pos = [float(c) for c in p.get("pos", t["start_pos"])]
        self.vel = [float(c) for c in p.get("vel", [0.0, 0.0])]
        self._tgt = None
        self._ramp_left = 0
        self.heading = float(p.get("heading_deg", t["start_heading_deg"]))
        self.oxygen_max = int(round(t["oxygen_max_s"] * TICK))
        self.oxygen_ticks = p.get("oxygen_ticks", self.oxygen_max)
        self.hp = p.get("hp", t["hp_max"])
        self.zero_oxy_ticks = p.get("zero_oxy_ticks", 0)
        self.invuln_ticks = p.get("invuln_ticks", 0)
        self.catch_cd_ticks = p.get("catch_cd_ticks", 0)
        self.hold = list(scenario.get("hold", []))  # thứ tự nhặt, cuối mảng là mới nhất
        self.time_left_ticks = scenario.get("time_left_ticks", int(round(t["duration_s"] * TICK)))
        self.steps = 0
        self.day = int(day)
        # nút và đàn cá: scenario THAY THẾ danh sách mặc định; random_fish=false tắt cá mặc định
        src_nodes = scenario["nodes"] if "nodes" in scenario else t["nodes"]
        self.nodes = [{"id": n["id"], "kind": n["kind"], "pos": [float(c) for c in n["pos"]],
                       "regrow_ticks": n.get("regrow_ticks", 0)} for n in src_nodes]
        if "fish" in scenario:
            src_fish = scenario["fish"]
        elif scenario.get("random_fish", True):
            src_fish = t["fish_initial"]
        else:
            src_fish = []
        # Đàn cá đứng yên ở phase này. Cá bơi / sinh thêm là việc của phase sau.
        self.fish = [{"id": f["id"], "kind": f["kind"], "pos": [float(c) for c in f["pos"]],
                      "heading_deg": float(f.get("heading_deg", 0)), "age_ticks": int(f.get("age_ticks", 0))}
                     for f in src_fish]
        for coll in (self.nodes, self.fish):
            for e in coll:
                ids.reserve(e["id"])
        self._init_monsters(scenario)
        self.money = 0
        self.earned = 0
        self.reputation = tuning["quan"]["reputation_initial"]
        self.done = False
        self.reason = None

    # --- giao diện cho runner -------------------------------------------------
    def inventory_items(self) -> dict:
        return hold_to_items(self.hold)

    def snapshot(self) -> dict:
        return {
            "player": {"pos": self.pos, "vel": self.vel, "heading_deg": self.heading,
                       "oxygen_ticks": self.oxygen_ticks, "oxygen_max_ticks": self.oxygen_max,
                       "hp": self.hp, "hp_max": self.t["hp_max"], "zero_oxy_ticks": self.zero_oxy_ticks,
                       "invuln_ticks": self.invuln_ticks, "catch_cd_ticks": self.catch_cd_ticks,
                       "at_surface": self._at_surface()},
            "hold": self.hold, "hold_count": len(self.hold),
            "hold_capacity": self.t["hold_capacity"],
            "nodes": [{"id": n["id"], "pos": n["pos"], "kind": n["kind"],
                       "ready": n["regrow_ticks"] == 0, "regrow_ticks": n["regrow_ticks"]}
                      for n in sort_by_id(self.nodes)],
            "fish": [{"id": f["id"], "pos": f["pos"], "kind": f["kind"], "heading_deg": f["heading_deg"],
                      "age_ticks": f["age_ticks"]} for f in sort_by_id(self.fish)],
            "monsters": [{"id": m["id"], "kind": m["kind"], "pos": m["pos"], "state": m["state"],
                          "state_ticks_left": m["state_ticks_left"]} for m in sort_by_id(self.monsters)],
        }

    # --- một bước ---------------------------------------------------------------
    def step(self, inp):
        events = []
        self.steps += 1
        # 1. đồng hồ và hàng có sẵn: giảm bộ đếm, nút mọc lại
        self.time_left_ticks = max(0, self.time_left_ticks - 1)
        self.invuln_ticks = max(0, self.invuln_ticks - 1)
        self.catch_cd_ticks = max(0, self.catch_cd_ticks - 1)
        for n in sort_by_id(self.nodes):
            if n["regrow_ticks"] > 0:
                n["regrow_ticks"] -= 1
                if n["regrow_ticks"] == 0:
                    events.append(("node_regrown", {"node_id": n["id"]}))
        # 2. bơi + chặn mép (chặn mép đã làm trong _move)
        was_surface = self._at_surface()
        self._move(inp)
        at_surface = self._at_surface()
        # 3. đổi vùng đầu/cuối bước -> dive / surface (data: pos)
        if was_surface and not at_surface:
            events.append(("dive", {"pos": list(self.pos)}))
        elif at_surface and not was_surface:
            events.append(("surface", {"pos": list(self.pos)}))
        # 4. oxy theo d CUỐI bước, rồi ngạt -> choke -> ngất
        if at_surface:
            self.oxygen_ticks = min(self.oxygen_max,
                                    self.oxygen_ticks + int(self.t["oxygen_refill_per_tick"]))
            self.zero_oxy_ticks = 0
        else:
            if self.oxygen_ticks > 0:
                self.oxygen_ticks -= 1
                if self.oxygen_ticks == 0:
                    events.append(("oxygen_empty", {"oxygen_ticks": 0}))
            if self.oxygen_ticks == 0:
                self.zero_oxy_ticks += 1
                if self.zero_oxy_ticks >= int(self.t["choke_interval_ticks"]):
                    self.zero_oxy_ticks = 0
                    self.hp -= 1
                    events.append(("choke", {"hp": self.hp}))
                    if self.hp <= 0:
                        self._faint(events)
                        return events
        # 4b. quái: cập nhật (patrol/chase/recoil) rồi xét tối đa một hit
        self._update_monsters(events)
        self._monster_hit(events)
        if self.done:
            return events
        # 5. interact: bến trước, rồi hái
        if inp.pressed("interact"):
            if self._in_dock():
                self._finish("docked", events)
                return events
            if self._at_surface():
                candidates = []
                radius = float(self.t["interact_radius"])
                for n in self.nodes:
                    if n["regrow_ticks"] == 0:
                        dist = math.dist(self.pos, n["pos"])
                        if dist <= radius:
                            candidates.append((dist, n))
                if candidates:
                    candidates.sort(key=lambda item: (item[0], id_key(item[1]["id"])))
                    _, target_node = candidates[0]
                    capacity = int(self.t["hold_capacity"])
                    free_space = capacity - len(self.hold)
                    yield_amt = int(self.t.get("node_yield", 1))
                    if free_space >= yield_amt:
                        self.hold.extend([target_node["kind"]] * yield_amt)
                        target_node["regrow_ticks"] = int(round(self.t["regrow_s"] * TICK))
                        events.append(("gather", {
                            "node_id": target_node["id"],
                            "kind": target_node["kind"],
                            "amount": yield_amt,
                        }))
                    else:
                        events.append(("hold_full", {
                            "action": "gather",
                            "node_id": target_node["id"],
                            "required": yield_amt,
                            "free": free_space,
                        }))
        # 6. bắt cá
        if inp.pressed("catch"):
            if self.catch_cd_ticks == 0 and not self._at_surface():
                candidates = []
                radius = float(self.t["catch_radius"])
                for f in self.fish:
                    dist = math.dist(self.pos, f["pos"])
                    if dist <= radius:
                        candidates.append((dist, f))
                if candidates:
                    candidates.sort(key=lambda item: (item[0], id_key(item[1]["id"])))
                    _, target_fish = candidates[0]
                    yield_amt = int(self.t["fish_yield"][target_fish["kind"]])
                    capacity = int(self.t["hold_capacity"])
                    free_space = capacity - len(self.hold)
                    if free_space >= yield_amt:
                        self.hold.extend([target_fish["kind"]] * yield_amt)
                        self.fish.remove(target_fish)
                        self.catch_cd_ticks = int(round(self.t["catch_cooldown_s"] * TICK))
                        events.append(("fish_caught", {
                            "fish_id": target_fish["id"],
                            "kind": target_fish["kind"],
                            "yield": yield_amt,
                        }))
                    else:
                        events.append(("hold_full", {
                            "action": "catch",
                            "fish_id": target_fish["id"],
                            "required": yield_amt,
                            "free": free_space,
                        }))
        # 7. hết giờ
        if self.time_left_ticks <= 0:
            self._finish("time", events)
            return events
        # 8. cá bơi, sinh thêm theo lịch
        self._move_fish(events)
        self._spawn_fish(events)
        return events

    # --- tiện ích ---------------------------------------------------------------
    def _at_surface(self) -> bool:
        return self.pos[1] <= self.t["surface_depth"]

    def _in_dock(self) -> bool:
        return math.dist(self.pos, self.t["dock_pos"]) <= self.t["dock_radius"]

    def _hold_full(self) -> bool:
        return len(self.hold) >= int(self.t["hold_capacity"])

    def _add_to_hold(self, item_id: str) -> bool:
        """Nhặt vào giỏ kiểu LIFO: món mới nhất nằm cuối; giỏ đầy thì không thêm (trả False)."""
        if self._hold_full():
            return False
        self.hold.append(item_id)
        return True

    def _faint(self, events, cause="choke"):
        """Ngất vì hết Máu: mất toàn bộ giỏ, kết thúc lượt với reason `fainted` (kho rỗng)."""
        lost = list(reversed(self.hold))
        self.hp = 0
        self.hold = []
        events.append(("faint", {"cause": cause, "lost": lost, "hp": 0}))
        self._finish("fainted", events)

    def _finish(self, reason, events):
        self.done = True
        self.reason = reason
        events.append(("gather_end", {"reason": reason, "inventory": {"items": self.inventory_items()}}))

    def _move(self, inp):
        speed = self.t["swim_speed"]
        mx, md = inp.move
        self.vel = ramp_velocity(self, (mx * speed, md * speed), int(self.t["ramp_max_ticks"]))
        if (mx, md) != (0.0, 0.0):
            self.heading = math.degrees(math.atan2(md, mx)) % 360
        b = self.t["bounds"]
        for i, axis in enumerate(AXES):
            self.pos[i] += self.vel[i] / TICK
            lo, hi = b[axis]
            if self.pos[i] <= lo:
                self.pos[i] = lo
                self.vel[i] = max(0.0, self.vel[i])
            elif self.pos[i] >= hi:
                self.pos[i] = hi
                self.vel[i] = min(0.0, self.vel[i])

    # --- cá bơi / sinh đàn (v1.1) ------------------------------------------------
    def _move_fish(self, events):
        speed = float(self.t["fish_speed"])
        turn = int(self.t["fish_turn_ticks"])
        lo_x, hi_x = self.t["fish_x"]
        rng = self.rng.get("fish_move")
        for i, f in enumerate(sort_by_id(self.fish)):
            if f["age_ticks"] > 0 and f["age_ticks"] % turn == 0:
                f["heading_deg"] = rng.uniform(0, 360)
            rad = math.radians(f["heading_deg"])
            x = f["pos"][0] + math.cos(rad) * speed / TICK
            d = f["pos"][1] + math.sin(rad) * speed / TICK
            lo_d, hi_d = self.t["fish_depths"][f["kind"]]
            if x < lo_x:
                x = lo_x + (lo_x - x)
                f["heading_deg"] = (180.0 - f["heading_deg"]) % 360.0
            elif x > hi_x:
                x = hi_x - (x - hi_x)
                f["heading_deg"] = (180.0 - f["heading_deg"]) % 360.0
            if d < lo_d:
                d = lo_d + (lo_d - d)
                f["heading_deg"] = (360.0 - f["heading_deg"]) % 360.0
            elif d > hi_d:
                d = hi_d - (d - hi_d)
                f["heading_deg"] = (360.0 - f["heading_deg"]) % 360.0
            f["pos"] = [min(hi_x, max(lo_x, x)), min(float(hi_d), max(float(lo_d), d))]
            f["age_ticks"] += 1

    def _spawn_fish(self, events):
        fp = self.t
        if self.steps % int(fp["fish_spawn_ticks"]) != 0:
            return
        if len(self.fish) >= int(fp["fish_max"]):
            return
        clearance = float(fp["fish_spawn_clearance"])
        points = []
        for kind, depths in fp["fish_spawn_depths"].items():
            for x in fp["fish_spawn_x"]:
                for d in depths:
                    if all(math.dist((x, d), f["pos"]) > clearance for f in self.fish):
                        points.append((kind, float(x), float(d)))
        if not points:
            return
        kinds = sorted({k for k, _, _ in points})
        weights = [float(fp["fish_weights"].get(k, 0)) for k in kinds]
        total = sum(weights)
        rng = self.rng.get("fish_spawn")
        pick = rng.random() * total
        acc = 0.0
        kind = kinds[-1]
        for k, w in zip(kinds, weights):
            acc += w
            if pick <= acc:
                kind = k
                break
        options = [(x, d) for k, x, d in points if k == kind]
        x, d = options[rng.randrange(len(options))]
        heading = rng.uniform(0, 360)
        fid = self.ids.new("F")
        self.fish.append({"id": fid, "kind": kind, "pos": [x, d], "heading_deg": heading, "age_ticks": 0})
        events.append(("fish_spawned", {"id": fid, "kind": kind, "pos": [x, d]}))

    # --- Cá Sấu (v1.1) -----------------------------------------------------------
    def _init_monsters(self, scenario):
        spec = self.t.get("monsters") or {}
        species = spec.get("species", {})
        src = scenario.get("monsters")
        if isinstance(src, dict):
            src = src.get("spawns", [])
        if src is None:
            src = [s for s in spec.get("spawns", []) if int(s.get("from_day", 1)) <= self.day]
        self.monsters = []
        for m in src or []:
            kind = m.get("kind")
            wps = [[float(c) for c in w] for w in m.get("waypoints", [])]
            if not wps:
                wps = [[float(c) for c in m.get("pos", [0, 0])]]
            mon = {"id": m["id"], "kind": kind, "pos": [float(c) for c in m.get("pos", wps[0])],
                   "waypoints": wps, "target_idx": int(m.get("target_idx", 1 if len(wps) > 1 else 0)),
                   "state": m.get("state", "patrol"), "state_ticks_left": int(m.get("state_ticks_left", 0)),
                   "recoil_dir": m.get("recoil_dir"), "spec": species.get(kind, {})}
            self.monsters.append(mon)
            self.ids.reserve(mon["id"])

    def _clamp_monster(self, mon, depths, bounds):
        lo = max(float(bounds["d"][0]), float(depths[0]))
        hi = min(float(bounds["d"][1]), float(depths[1]))
        mon["pos"][0] = min(float(bounds["x"][1]), max(float(bounds["x"][0]), mon["pos"][0]))
        mon["pos"][1] = min(hi, max(lo, mon["pos"][1]))

    def _move_toward(self, mon, target, speed, depths, bounds):
        dx = float(target[0]) - mon["pos"][0]
        dy = float(target[1]) - mon["pos"][1]
        dist = math.hypot(dx, dy)
        step = speed / TICK
        if dist <= step or dist == 0:
            mon["pos"] = [float(target[0]), float(target[1])]
        else:
            mon["pos"][0] += dx / dist * step
            mon["pos"][1] += dy / dist * step
        self._clamp_monster(mon, depths, bounds)

    def _update_monsters(self, events):
        bounds = self.t["bounds"]
        for mon in sort_by_id(self.monsters):
            sp = mon["spec"]
            depths = sp.get("depths", [10, 30])
            if mon["state"] == "recoil":
                mon["state_ticks_left"] -= 1
                dirv = mon.get("recoil_dir") or [1.0, 0.0]
                step = float(sp.get("recoil_dist", 2.0)) / max(1.0, float(sp.get("recoil_ticks", 60)))
                mon["pos"][0] += dirv[0] * step
                mon["pos"][1] += dirv[1] * step
                self._clamp_monster(mon, depths, bounds)
                if mon["state_ticks_left"] <= 0:
                    mon["state"] = "patrol"
                    mon["recoil_dir"] = None
                continue
            deep = self.pos[1] >= 10
            dist = math.dist(mon["pos"], self.pos)
            if mon["state"] == "patrol" and deep and dist <= float(sp.get("detect_radius", 10)):
                mon["state"] = "chase"
            elif mon["state"] == "chase" and (not deep or dist > float(sp.get("exit_radius", 16))):
                mon["state"] = "patrol"
            if mon["state"] == "chase":
                self._move_toward(mon, self.pos, float(sp.get("chase_speed", 3.0)), depths, bounds)
            else:
                wp = mon["waypoints"][mon["target_idx"]] if mon["waypoints"] else mon["pos"]
                self._move_toward(mon, wp, float(sp.get("patrol_speed", 1.0)), depths, bounds)
                if len(mon["waypoints"]) == 2 and math.dist(mon["pos"], wp) < 0.05:
                    mon["target_idx"] = 1 - mon["target_idx"]

    def _monster_hit(self, events):
        if self.invuln_ticks > 0 or self.pos[1] < 10:
            return
        hits = []
        for mon in sort_by_id(self.monsters):
            if mon["state"] == "recoil":
                continue
            reach = float(mon["spec"].get("hit_radius", 1.5))
            dist = math.dist(mon["pos"], self.pos)
            if dist <= reach:
                hits.append((dist, mon))
        if not hits:
            return
        hits.sort(key=lambda item: (item[0], id_key(item[1]["id"])))
        mon = hits[0][1]
        self.hp -= 1
        lost = [self.hold.pop() for _ in range(len(self.hold) // 2)]
        self.invuln_ticks = int(self.t.get("invuln_ticks", 90))
        dx = mon["pos"][0] - self.pos[0]
        dy = mon["pos"][1] - self.pos[1]
        norm = math.hypot(dx, dy)
        mon["recoil_dir"] = [1.0, 0.0] if norm == 0 else [dx / norm, dy / norm]
        mon["state"] = "recoil"
        mon["state_ticks_left"] = int(mon["spec"].get("recoil_ticks", 60))
        events.append(("monster_hit", {"monster_id": mon["id"], "hp": self.hp, "lost": lost, "pos": list(self.pos)}))
        if self.hp <= 0:
            self._faint(events, cause="monster")
