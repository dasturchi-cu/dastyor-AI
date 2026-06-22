#!/usr/bin/env python3
"""Backup SQLite database and uploads to a timestamped archive under DATA_DIR/backups."""
from __future__ import annotations

import argparse
import shutil
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

from config.paths import ensure_data_dirs
from config.settings import DATA_DIR, GENERATED_DIR, RECEIPTS_DIR, settings


def _backup_db(dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    src = settings.db_path
    if not src.is_file():
        raise FileNotFoundError(f"Database not found: {src}")
    with sqlite3.connect(src) as conn:
        with sqlite3.connect(dest) as out:
            conn.backup(out)
    ok, msg = _integrity(dest)
    if not ok:
        dest.unlink(missing_ok=True)
        raise RuntimeError(f"Backup integrity check failed: {msg}")


def _integrity(path: Path) -> tuple[bool, str]:
    with sqlite3.connect(path) as conn:
        row = conn.execute("PRAGMA integrity_check").fetchone()
    msg = str(row[0]) if row else "unknown"
    return msg == "ok", msg


def main() -> int:
    parser = argparse.ArgumentParser(description="Backup Hujjatchi SQLite + uploads")
    parser.add_argument(
        "--uploads",
        action="store_true",
        help="Also copy receipts and generated files",
    )
    args = parser.parse_args()

    ensure_data_dirs()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_root = DATA_DIR / "backups" / stamp
    backup_root.mkdir(parents=True, exist_ok=True)

    db_dest = backup_root / "hujjatchi.db"
    _backup_db(db_dest)
    print(f"DB backup: {db_dest}")

    if args.uploads:
        for src in (RECEIPTS_DIR, GENERATED_DIR):
            if src.is_dir() and any(src.iterdir()):
                dest = backup_root / src.name
                shutil.copytree(src, dest, dirs_exist_ok=True)
                print(f"Copied: {src} -> {dest}")

    # Keep last 14 backup folders
    backups_dir = DATA_DIR / "backups"
    folders = sorted(p for p in backups_dir.iterdir() if p.is_dir())
    for old in folders[:-14]:
        shutil.rmtree(old, ignore_errors=True)

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"backup failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
