"""Runtime data paths — persistent storage (not repo temp/)."""
from __future__ import annotations

from pathlib import Path

from config.settings import DATA_DIR, GENERATED_DIR, RECEIPTS_DIR, UPLOADS_DIR, settings


def temp_dir() -> Path:
    """Ephemeral processing files (voice, docx build) under persistent DATA_DIR."""
    path = DATA_DIR / "tmp"
    path.mkdir(parents=True, exist_ok=True)
    return path


def sessions_file() -> Path:
    path = DATA_DIR / "sessions.json"
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return path


def ensure_data_dirs() -> None:
    for path in (DATA_DIR, UPLOADS_DIR, RECEIPTS_DIR, GENERATED_DIR, temp_dir()):
        path.mkdir(parents=True, exist_ok=True)
    settings.db_path.parent.mkdir(parents=True, exist_ok=True)
