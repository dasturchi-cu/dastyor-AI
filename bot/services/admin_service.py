"""
Admin management service.
Persistent storage: admins.json
Action audit: admin_actions.log
"""
import json
import os
from datetime import datetime

ADMINS_FILE = "admins.json"
ACTIONS_LOG = "admin_actions.log"


def _parse_ids(raw: str) -> list[int]:
    ids: list[int] = []
    for part in (raw or "").split(","):
        p = part.strip()
        if p.isdigit():
            ids.append(int(p))
    return ids


def _load_data() -> dict:
    env_seed = _parse_ids(os.getenv("ADMIN_USER_ID", ""))
    if not os.path.exists(ADMINS_FILE):
        return {"admins": env_seed}
    try:
        with open(ADMINS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = {"admins": []}
    admins = data.get("admins", [])
    if not isinstance(admins, list):
        admins = []
    normalized = []
    for v in admins:
        try:
            iv = int(v)
            normalized.append(iv)
        except Exception:
            continue
    # Keep env admins always present (backward-compatible bootstrap).
    for ev in env_seed:
        if ev not in normalized:
            normalized.append(ev)
    return {"admins": sorted(set(normalized))}


def _save_data(data: dict) -> None:
    with open(ADMINS_FILE, "w", encoding="utf-8") as f:
        json.dump({"admins": sorted(set(data.get("admins", [])))}, f, ensure_ascii=False, indent=2)


def _log_action(actor_id: int, action: str, target_id: int, actor_username: str | None = None) -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    actor_un = f"@{actor_username}" if actor_username else "unknown"
    line = f"{ts} | actor_id={actor_id} | actor_username={actor_un} | action={action} | target_user_id={target_id}\n"
    with open(ACTIONS_LOG, "a", encoding="utf-8") as f:
        f.write(line)


def is_admin(user_id: int | str) -> bool:
    try:
        uid = int(user_id)
    except Exception:
        return False
    data = _load_data()
    return uid in data["admins"]


def list_admins() -> list[int]:
    return _load_data()["admins"]


def add_admin(
    *,
    actor_id: int,
    target_user_id: int,
    actor_username: str | None = None,
) -> tuple[bool, str]:
    data = _load_data()
    admins = data["admins"]
    if target_user_id in admins:
        return False, "Bu foydalanuvchi allaqachon admin."
    admins.append(int(target_user_id))
    data["admins"] = sorted(set(admins))
    _save_data(data)
    _log_action(actor_id, "add_admin", int(target_user_id), actor_username)
    return True, "✅ Admin muvaffaqiyatli qo'shildi."


def remove_admin(
    *,
    actor_id: int,
    target_user_id: int,
    actor_username: str | None = None,
) -> tuple[bool, str]:
    data = _load_data()
    admins = data["admins"]
    if target_user_id not in admins:
        return False, "Bu foydalanuvchi admin emas."
    if len(admins) <= 1:
        return False, "Oxirgi adminni o'chirib bo'lmaydi."
    admins = [x for x in admins if x != int(target_user_id)]
    data["admins"] = admins
    _save_data(data)
    _log_action(actor_id, "remove_admin", int(target_user_id), actor_username)
    return True, "✅ Admin ro'yxatdan o'chirildi."
