"""File kho v1.2 (Contract v1.2, TICKET-03): kho cá thể {"items": [{"id": ..., "kind": ..., "fresh": ...}]}.

Đọc: từ chối sai schema / id lạ / id trùng / fresh ngoài miền / kho đếm ở v1.2 (BadInput -> mã 2).
Ghi: qua file tạm cùng thư mục rồi thay thế nguyên tử, sắp theo id.
"""

import json
import math
import os
import tempfile

from .errors import BadInput
from .ids import sort_by_id
from .jsonl import _clean

KINDS_ALL = ("ca_loc", "ca_linh", "ca_keo", "bong_dien_dien", "bong_sung", "keo_neo")
KINDS_P1 = KINDS_ALL


def validate_items(items, kinds=KINDS_ALL):
    if not isinstance(items, dict):
        raise BadInput("items phải là object")
    out = {}
    for k, v in items.items():
        if k not in kinds:
            raise BadInput(f"nguyên liệu lạ: {k}")
        if isinstance(v, bool) or not isinstance(v, int) or v < 0:
            raise BadInput(f"số lượng không hợp lệ cho {k}: {v!r}")
        if v > 0:
            out[k] = v
    return out


def validate_individual_items(items, kinds=KINDS_ALL):
    if not isinstance(items, list):
        raise BadInput("items phải là mảng cá thể")
    seen_ids = set()
    validated = []
    for it in items:
        if not isinstance(it, dict) or set(it.keys()) != {"id", "kind", "fresh"}:
            raise BadInput(f"cá thể kho không đúng schema {{id, kind, fresh}}: {it!r}")
        iid = it.get("id")
        if not isinstance(iid, str) or not iid:
            raise BadInput(f"id không hợp lệ: {iid!r}")
        if iid in seen_ids:
            raise BadInput(f"id trùng trong kho: {iid}")
        seen_ids.add(iid)
        kind = it.get("kind")
        if kind not in kinds:
            raise BadInput(f"nguyên liệu lạ trong kho: {kind}")
        fresh = it.get("fresh")
        if isinstance(fresh, bool) or not isinstance(fresh, (int, float)) or not math.isfinite(fresh):
            raise BadInput(f"fresh không hợp lệ: {fresh!r}")
        if not (0.0 <= fresh <= 100.0):
            raise BadInput(f"fresh ngoài miền [0, 100]: {fresh}")
        validated.append({"id": iid, "kind": kind, "fresh": round(float(fresh), 3)})
    return validated


def read_inventory(path: str, kinds=KINDS_ALL, contract_version="1.2"):
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError) as e:
        raise BadInput(f"không đọc được file kho {path}: {e}")
    if not isinstance(data, dict) or set(data.keys()) != {"items"}:
        raise BadInput("file kho chỉ được có khóa gốc 'items'")
    items = data["items"]
    if contract_version >= "1.2":
        if isinstance(items, dict):
            raise BadInput("Contract v1.2: kho đếm không được hỗ trợ (cần kho cá thể mảng items)")
        return validate_individual_items(items, kinds)
    else:
        if isinstance(items, dict):
            return validate_items(items, kinds)
        elif isinstance(items, list):
            return validate_individual_items(items, kinds)
        else:
            raise BadInput("items phải là mảng hoặc object")


def hold_to_items(hold: list):
    """Giỏ -> danh sách cá thể kho v1.2, hoặc dict đếm nếu hold là mảng tên loại."""
    if not hold:
        return []
    if isinstance(hold[0], dict):
        return sort_by_id(list(hold))
    counts = {}
    for k in hold:
        counts[k] = counts.get(k, 0) + 1
    return {k: counts[k] for k in sorted(counts)}


def write_inventory(path: str, items):
    if isinstance(items, dict) and "items" in items and isinstance(items["items"], list):
        items_list = items["items"]
    elif isinstance(items, list):
        items_list = items
    elif isinstance(items, dict):
        items_list = items
    else:
        items_list = []

    if isinstance(items_list, list):
        payload = {"items": sort_by_id(items_list)}
    else:
        payload = {"items": {k: items_list[k] for k in sorted(items_list) if items_list[k] > 0}}
    payload = _clean(payload)

    d = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(prefix=".inv-", suffix=".tmp", dir=d)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
            f.write("\n")
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise
