"""
Premium purchase persistence (SQLite).

Stores:
- payment_requests: uploaded checks waiting for admin decision
- premium_subscriptions: approved premium periods
"""
import os
import sqlite3
from datetime import datetime
from typing import Optional

DB_PATH = os.path.join("temp", "premium_purchase.db")


def _conn() -> sqlite3.Connection:
    os.makedirs("temp", exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def _init_db() -> None:
    with _conn() as con:
        cur = con.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS payment_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                username TEXT,
                first_name TEXT,
                plan_type TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT NOT NULL,
                reviewed_at TEXT,
                reviewer_id INTEGER
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS premium_subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                plan_type TEXT NOT NULL,
                start_date TEXT NOT NULL,
                expire_date TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_payreq_user ON payment_requests(user_id)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_payreq_status ON payment_requests(status)"
        )
        cur.execute(
            "CREATE INDEX IF NOT EXISTS idx_sub_user ON premium_subscriptions(user_id)"
        )
        con.commit()


def create_payment_request(
    user_id: int,
    plan_type: str,
    username: str = "",
    first_name: str = "",
) -> int:
    _init_db()
    plan = (plan_type or "premium").strip().lower()
    if plan not in ("standard", "premium"):
        plan = "premium"
    now = datetime.utcnow().isoformat()
    with _conn() as con:
        cur = con.cursor()
        cur.execute(
            """
            INSERT INTO payment_requests (user_id, username, first_name, plan_type, status, created_at)
            VALUES (?, ?, ?, ?, 'pending', ?)
            """,
            (int(user_id), username or "", first_name or "", plan, now),
        )
        con.commit()
        return int(cur.lastrowid)


def get_payment_request(request_id: int) -> Optional[dict]:
    _init_db()
    with _conn() as con:
        cur = con.cursor()
        cur.execute("SELECT * FROM payment_requests WHERE id = ?", (int(request_id),))
        row = cur.fetchone()
        return dict(row) if row else None


def set_payment_request_status(request_id: int, status: str, reviewer_id: int | None = None) -> bool:
    _init_db()
    st = (status or "").strip().lower()
    if st not in ("approved", "rejected"):
        return False
    with _conn() as con:
        cur = con.cursor()
        cur.execute(
            """
            UPDATE payment_requests
            SET status = ?, reviewed_at = ?, reviewer_id = ?
            WHERE id = ? AND status = 'pending'
            """,
            (st, datetime.utcnow().isoformat(), int(reviewer_id) if reviewer_id else None, int(request_id)),
        )
        con.commit()
        return cur.rowcount > 0


def save_subscription(user_id: int, plan_type: str, start_date: str, expire_date: str) -> int:
    _init_db()
    plan = (plan_type or "premium").strip().lower()
    if plan not in ("standard", "premium"):
        plan = "premium"
    with _conn() as con:
        cur = con.cursor()
        cur.execute(
            """
            INSERT INTO premium_subscriptions (user_id, plan_type, start_date, expire_date, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (int(user_id), plan, start_date, expire_date, datetime.utcnow().isoformat()),
        )
        con.commit()
        return int(cur.lastrowid)

