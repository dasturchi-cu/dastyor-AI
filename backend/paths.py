"""Absolute paths to repo assets (avoid CWD-dependent 404 for StaticFiles)."""
from __future__ import annotations

from pathlib import Path

# backend/paths.py → repo root is parent of backend/
_REPO_ROOT = Path(__file__).resolve().parent.parent


def repo_root() -> Path:
    return _REPO_ROOT


def webapp_dir() -> Path:
    return _REPO_ROOT / "webapp"


def webapp_index_path() -> Path:
    return _REPO_ROOT / "webapp" / "index.html"
