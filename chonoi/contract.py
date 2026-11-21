"""Đọc game.contract.json và kiểm dải hợp lệ của tuning P1 (PRD mục 13.2, Test Contract)."""

import json
import os

from .errors import BadInput

DEFAULT_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game.contract.json")


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _between(name, v, lo, hi):
    if not _num(v) or not (lo <= v <= hi):
        raise BadInput(f"tuning.{name} phải trong [{lo}, {hi}], đang là {v!r}")


def load_contract(path=DEFAULT_PATH) -> dict:
    try:
        with open(path, encoding="utf-8") as f:
            c = json.load(f)
    except (OSError, ValueError) as e:
        raise BadInput(f"không đọc được {path}: {e}")
    validate_tuning(c.get("tuning"))
    return c


def _int_between(name, v, lo, hi):
    if isinstance(v, bool) or not isinstance(v, int) or not (lo <= v <= hi):
        raise BadInput(f"tuning.{name} phải là số nguyên trong [{lo}, {hi}], đang là {v!r}")


def _pos_in(name, pos, bounds, keys):
    if (not isinstance(pos, list) or len(pos) != 2 or not all(_num(c) for c in pos)):
        raise BadInput(f"tuning.{name} phải là [số, số]")
    for c, k in zip(pos, keys):
        lo, hi = bounds[k]
        if not (lo <= c <= hi):
            raise BadInput(f"tuning.{name} nằm ngoài vùng {k} ∈ [{lo}, {hi}]")


def _bounds(name, b, keys):
    if not isinstance(b, dict) or set(b) != set(keys):
        raise BadInput(f"tuning.{name}.bounds phải có đúng khóa {list(keys)}")
    for k in keys:
        v = b[k]
        if not (isinstance(v, list) and len(v) == 2 and all(_num(c) for c in v) and v[0] == 0 and v[1] > 0):
            raise BadInput(f"tuning.{name}.bounds.{k} phải là [0, số dương]")


def _validate_gather(g):
    """Dải hợp lệ P1 theo PRD mục 13.2."""
    _between("gather.duration_s", g.get("duration_s"), 60, 600)
    _bounds("gather", g.get("bounds"), ("x", "d"))
    b = g["bounds"]
    _between("gather.dock_radius", g.get("dock_radius"), 0.5, 5)
    _between("gather.interact_radius", g.get("interact_radius"), 0.5, 5)
    _between("gather.catch_radius", g.get("catch_radius"), 0.5, 5)
    _between("gather.swim_speed", g.get("swim_speed"), 1, 10)
    _between("gather.catch_cooldown_s", g.get("catch_cooldown_s"), 0, 10)
    _between("gather.oxygen_max_s", g.get("oxygen_max_s"), 10, 120)
    _int_between("gather.ramp_max_ticks", g.get("ramp_max_ticks"), 0, 6)
    _int_between("gather.hold_capacity", g.get("hold_capacity"), 4, 30)
    _int_between("gather.hp_max", g.get("hp_max"), 1, 99)
    _int_between("gather.oxygen_refill_per_tick", g.get("oxygen_refill_per_tick"), 1, 10_000)
    _int_between("gather.choke_interval_ticks", g.get("choke_interval_ticks"), 1, 10_000)
    _int_between("gather.node_yield", g.get("node_yield"), 1, 12)
    _between("gather.regrow_s", g.get("regrow_s"), 0.1, 600)
    _between("gather.surface_depth", g.get("surface_depth"), 0, 5)
    _pos_in("gather.dock_pos", g.get("dock_pos"), b, ("x", "d"))
    _pos_in("gather.start_pos", g.get("start_pos"), b, ("x", "d"))
    if not _num(g.get("start_heading_deg")):
        raise BadInput("tuning.gather.start_heading_deg phải là số")
    fy = g.get("fish_yield")
    if not isinstance(fy, dict) or not {"ca_linh", "ca_loc", "ca_keo"} <= set(fy):
        raise BadInput("tuning.gather.fish_yield phải có ca_linh và ca_loc")
    for k, v in fy.items():
        _int_between(f"gather.fish_yield.{k}", v, 1, g["hold_capacity"])
    nodes = g.get("nodes")
    if not isinstance(nodes, list) or not nodes:
        raise BadInput("tuning.gather.nodes phải là mảng không rỗng")
    seen, kinds = set(), set()
    for n in nodes:
        if not isinstance(n, dict) or not isinstance(n.get("id"), str) or n["id"] in seen:
            raise BadInput("tuning.gather.nodes: mỗi nút cần id duy nhất")
        seen.add(n["id"])
        if n.get("kind") not in ("bong_dien_dien", "bong_sung", "keo_neo"):
            raise BadInput(f"tuning.gather.nodes.{n['id']}: kind phải là bong_dien_dien hoặc bong_sung")
        kinds.add(n["kind"])
        _pos_in(f"gather.nodes.{n['id']}.pos", n.get("pos"), b, ("x", "d"))
        if n["pos"][1] != 0:
            raise BadInput(f"tuning.gather.nodes.{n['id']}: nút hái nằm ở mặt nước (d = 0)")
    if not {"bong_dien_dien", "bong_sung", "keo_neo"} <= kinds:
        raise BadInput("tuning.gather.nodes phải có ít nhất một nút mỗi loại (bong_dien_dien, bong_sung)")
    fish = g.get("fish_initial")
    if not isinstance(fish, list) or len(fish) != 8:
        raise BadInput("tuning.gather.fish_initial phải là danh sách đúng 6 đàn")
    seen = set()
    for f in fish:
        if not isinstance(f, dict) or not isinstance(f.get("id"), str) or f["id"] in seen:
            raise BadInput("tuning.gather.fish_initial: mỗi đàn cần id duy nhất")
        seen.add(f["id"])
        if f.get("kind") not in fy:
            raise BadInput(f"tuning.gather.fish_initial.{f['id']}: kind phải thuộc fish_yield")
        _pos_in(f"gather.fish_initial.{f['id']}.pos", f.get("pos"), b, ("x", "d"))
        if f["pos"][1] <= g["surface_depth"]:
            raise BadInput(f"tuning.gather.fish_initial.{f['id']}: đàn cá phải ở dưới nước")


def _validate_fish_meta(g):
    _between("gather.fish_speed", g.get("fish_speed"), 0.1, 10)
    _int_between("gather.fish_turn_ticks", g.get("fish_turn_ticks"), 1, 100000)
    _int_between("gather.fish_max", g.get("fish_max"), 1, 100)
    _int_between("gather.fish_spawn_ticks", g.get("fish_spawn_ticks"), 1, 100000)
    _between("gather.fish_spawn_clearance", g.get("fish_spawn_clearance"), 0, 50)
    fx = g.get("fish_x")
    if not (isinstance(fx, list) and len(fx) == 2 and all(_num(c) for c in fx) and fx[0] < fx[1]):
        raise BadInput("gather.fish_x phải là [x0, x1]")
    for name in ("fish_depths", "fish_spawn_depths"):
        m = g.get(name)
        if not isinstance(m, dict) or not {"ca_linh", "ca_loc", "ca_keo"} <= set(m):
            raise BadInput(f"gather.{name} phải có đủ 3 loài")
        for k, band in m.items():
            if not (isinstance(band, list) and len(band) == 2 and all(_num(c) for c in band) and band[0] <= band[1]):
                raise BadInput(f"gather.{name}.{k} phải là [d0, d1]")
    sx = g.get("fish_spawn_x")
    if not (isinstance(sx, list) and sx and all(_num(c) for c in sx)):
        raise BadInput("gather.fish_spawn_x phải là mảng số")
    w = g.get("fish_weights")
    if not isinstance(w, dict) or not w or not all(_num(v) and v > 0 for v in w.values()):
        raise BadInput("gather.fish_weights phải là map loài -> trọng số > 0")


def _validate_monsters(g):
    m = g.get("monsters")
    if m is None:
        return
    if not isinstance(m, dict) or not isinstance(m.get("species"), dict) or not isinstance(m.get("spawns"), list):
        raise BadInput("gather.monsters phải có species và spawns")
    for kind, sp in m["species"].items():
        for key in ("patrol_speed", "chase_speed", "detect_radius", "exit_radius", "hit_radius", "recoil_ticks", "recoil_dist"):
            if not _num(sp.get(key)):
                raise BadInput(f"gather.monsters.species.{kind}.{key} phải là số")
        band = sp.get("depths")
        if not (isinstance(band, list) and len(band) == 2 and all(_num(c) for c in band)):
            raise BadInput(f"gather.monsters.species.{kind}.depths phải là [d0, d1]")
    seen = set()
    for s in m["spawns"]:
        if not isinstance(s, dict) or not isinstance(s.get("id"), str) or s["id"] in seen:
            raise BadInput("gather.monsters.spawns: mỗi con cần id duy nhất")
        seen.add(s["id"])
        if s.get("kind") not in m["species"]:
            raise BadInput(f"gather.monsters.spawns.{s['id']}: kind lạ")
        if not (isinstance(s.get("waypoints"), list) and len(s["waypoints"]) == 2):
            raise BadInput(f"gather.monsters.spawns.{s['id']}: cần 2 waypoint")
    for key, lo, hi in (("invuln_ticks", 0, 10000), ("loss_ratio", 0, 1)):
        v = g.get(key)
        if not _num(v) or not (lo <= v <= hi):
            raise BadInput(f"gather.{key} phải trong [{lo}, {hi}]")


def _validate_day_plan(t):
    plan = t.get("day_plan")
    if plan is None:
        return
    if not isinstance(plan, list) or len(plan) != 5:
        raise BadInput("tuning.day_plan phải có đúng 5 Ngày")
    for i, d in enumerate(plan, 1):
        if not isinstance(d, dict) or d.get("day") != i:
            raise BadInput(f"tuning.day_plan[{i-1}].day phải là {i}")
        for key in ("dishes", "ingredients"):
            m = d.get(key)
            if not isinstance(m, dict) or not m or not all(isinstance(v, int) and not isinstance(v, bool) and v > 0 for v in m.values()):
                raise BadInput(f"tuning.day_plan[{i-1}].{key} phải là map id -> số nguyên dương")


def _validate_shop(t):
    shop = t.get("shop")
    if shop is None:
        return
    if not isinstance(shop, dict) or not isinstance(shop.get("upgrades"), dict):
        raise BadInput("tuning.shop phải có upgrades")
    _int_between("shop.max_ticks", shop.get("max_ticks"), 1, 100000)
    up = shop["upgrades"]
    for name in ("oxygen", "hp"):
        arr = up.get(name)
        if not isinstance(arr, list) or not arr:
            raise BadInput(f"tuning.shop.upgrades.{name} phải là mảng không rỗng")
        for i, item in enumerate(arr, 1):
            if not isinstance(item, dict) or item.get("level") != i:
                raise BadInput(f"tuning.shop.upgrades.{name}[{i-1}].level phải là {i}")
            if isinstance(item.get("price"), bool) or not isinstance(item.get("price"), int) or item["price"] <= 0:
                raise BadInput(f"tuning.shop.upgrades.{name}[{i-1}].price phải là số nguyên dương")


def validate_tuning(t):
    if not isinstance(t, dict):
        raise BadInput("thiếu khối tuning")
    g, q, menu = t.get("gather"), t.get("quan"), t.get("menu")
    if not isinstance(g, dict) or not isinstance(q, dict) or not isinstance(menu, dict):
        raise BadInput("tuning phải có gather, quan, menu")
    _validate_gather(g)
    _validate_fish_meta(g)
    _validate_monsters(g)
    _validate_day_plan(t)
    _validate_shop(t)
    # Quán: dải hợp lệ P1 (PRD mục 13.2)
    _between("quan.duration_s", q.get("duration_s"), 60, 600)
    _bounds("quan", q.get("bounds"), ("x", "z"))
    _between("quan.patience_s", q.get("patience_s"), 20, 180)
    _between("quan.walk_speed", q.get("walk_speed"), 1, 10)
    _between("quan.interact_radius", q.get("interact_radius"), 0.5, 5)
    _int_between("quan.ramp_max_ticks", q.get("ramp_max_ticks", 6), 0, 6)
    _between("quan.eat_s", q.get("eat_s"), 0.1, 600)
    _between("quan.customer_interval_s", q.get("customer_interval_s"), 0.1, 600)
    _int_between("quan.first_customer_tick", q.get("first_customer_tick"), 1, int(q["duration_s"] * 60) - 1)
    if not (_num(q.get("tip_rate")) and q["tip_rate"] > 0 and _num(q.get("left_reputation_delta"))
            and q["left_reputation_delta"] < 0):
        raise BadInput("tip_rate phải > 0 và left_reputation_delta phải < 0")
    ratio = q.get("tip_min_patience_ratio")
    if not (_num(ratio) and 0 < ratio <= 1):
        raise BadInput("quan.tip_min_patience_ratio phải thuộc (0, 1]")
    if not (_num(q.get("tip_reputation")) and q["tip_reputation"] > 0):
        raise BadInput("quan.tip_reputation phải > 0")
    if q.get("burn_s") is not None:
        raise BadInput("burn_s phải là null ở Phase 1")
    # TODO(nhóm): bổ sung kiểm các khóa còn lại nếu muốn chặt hơn (bếp/bàn, uy tín, ...).
    for dish_id, d in menu.items():
        price, cook = d.get("price"), d.get("cook_s")
        if isinstance(price, bool) or not isinstance(price, int) or price <= 0 or not _num(cook) or cook <= 0:
            raise BadInput(f"menu.{dish_id}: price (nguyên) và cook_s phải > 0")
