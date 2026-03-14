"""
Support Requests Service
Stores and manages support requests from webapp and bot in a single place.
"""
import json
import os
import threading
from datetime import datetime
from typing import Any

SUPPORT_FILE = "support_requests.json"
_LOCK = threading.Lock()


def _load() -> dict[str, Any]:
    if not os.path.exists(SUPPORT_FILE):
        return {"last_id": 0, "items": []}
    try:
        with open(SUPPORT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return {"last_id": 0, "items": []}
        if "last_id" not in data:
            data["last_id"] = 0
        if "items" not in data or not isinstance(data["items"], list):
            data["items"] = []
        return data
    except Exception:
        return {"last_id": 0, "items": []}


def _save(data: dict[str, Any]) -> None:
    with open(SUPPORT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def create_support_request(
    *,
    user_id: int,
    username: str | None,
    message: str,
    source: str = "webapp",
) -> dict[str, Any]:
    with _LOCK:
        data = _load()
        data["last_id"] += 1
        item = {
            "id": data["last_id"],
            "user_id": int(user_id),
            "username": (username or "").strip(),
            "message": (message or "").strip(),
            "source": source,
            "status": "open",
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "resolved_at": None,
        }
        data["items"].append(item)
        _save(data)
        return item


def list_support_requests(*, status: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
    data = _load()
    items = data.get("items", [])
    if status:
        items = [x for x in items if x.get("status") == status]
    items = sorted(items, key=lambda x: x.get("id", 0), reverse=True)
    return items[: max(1, int(limit))]


def get_support_request(req_id: int) -> dict[str, Any] | None:
    data = _load()
    for item in data.get("items", []):
        if int(item.get("id", -1)) == int(req_id):
            return item
    return None


def set_support_status(req_id: int, status: str) -> bool:
    if status not in {"open", "resolved"}:
        return False
    with _LOCK:
        data = _load()
        changed = False
        for item in data.get("items", []):
            if int(item.get("id", -1)) == int(req_id):
                item["status"] = status
                item["resolved_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S") if status == "resolved" else None
                changed = True
                break
        if changed:
            _save(data)
        return changed


def support_stats() -> dict[str, int]:
    data = _load()
    items = data.get("items", [])
    open_count = sum(1 for x in items if x.get("status") == "open")
    resolved_count = sum(1 for x in items if x.get("status") == "resolved")
    return {
        "total": len(items),
        "open": open_count,
        "resolved": resolved_count,
    }
