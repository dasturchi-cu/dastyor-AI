import os
import time


def ensure_temp_dir() -> str:
    temp_dir = "temp"
    os.makedirs(temp_dir, exist_ok=True)
    return temp_dir


def temp_file_path(prefix: str, user_id: int | str, ext: str) -> str:
    safe_ext = str(ext or "").strip().lower().lstrip(".") or "tmp"
    return os.path.join(
        ensure_temp_dir(),
        f"{prefix}_{user_id}_{int(time.time())}.{safe_ext[:8]}",
    )


def safe_unlink(path: str | None) -> None:
    if not path:
        return
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception:
        pass
