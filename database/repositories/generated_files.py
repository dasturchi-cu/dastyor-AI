"""Generated files — cv_documents / obyektivka_documents + admin view."""
from __future__ import annotations

from typing import Any

from database.connection import get_connection, row_to_dict
from database.repositories import admin_data
from database.repositories import users as users_repo


def record_file(
    telegram_id: int,
    file_type: str,
    file_path: str,
    file_name: str | None = None,
    *,
    template_name: str | None = None,
    pdf_preview_path: str | None = None,
) -> dict[str, Any] | None:
    user = users_repo.get_by_telegram_id(telegram_id)
    if not user:
        user = users_repo.upsert_user(telegram_id)
    uid = int(user["id"])
    ft = file_type.lower()
    if ft not in ("cv", "obyektivka"):
        raise ValueError("file_type must be cv or obyektivka")

    with get_connection() as conn:
        if ft == "cv":
            cur = conn.execute(
                """
                INSERT INTO cv_documents (user_id, template_name, pdf_path)
                VALUES (?, ?, ?)
                """,
                (uid, template_name or file_name, file_path),
            )
            fid = cur.lastrowid
            conn.execute(
                """
                UPDATE users SET total_cv = total_cv + 1, updated_at = datetime('now')
                WHERE id = ?
                """,
                (uid,),
            )
            conn.execute(
                """
                INSERT INTO documents (user_id, document_type, file_path, is_unlocked)
                VALUES (?, 'cv', ?, 1)
                """,
                (uid, file_path),
            )
        else:
            cur = conn.execute(
                """
                INSERT INTO obyektivka_documents (user_id, docx_path, pdf_preview_path)
                VALUES (?, ?, ?)
                """,
                (uid, file_path, pdf_preview_path),
            )
            fid = cur.lastrowid
            conn.execute(
                """
                UPDATE users SET total_obyektivka = total_obyektivka + 1,
                    updated_at = datetime('now')
                WHERE id = ?
                """,
                (uid,),
            )
            conn.execute(
                """
                INSERT INTO documents (user_id, document_type, file_path, is_unlocked)
                VALUES (?, 'obyektivka', ?, 1)
                """,
                (uid, file_path),
            )
        row = conn.execute(
            "SELECT * FROM generated_files WHERE id = ? AND file_type = ?",
            (fid, ft),
        ).fetchone()

    users_repo.invalidate_cache(telegram_id)
    data = row_to_dict(row)
    if data:
        from shared.activity import log_cv, log_download, log_obyektivka

        name = (
            str(user.get("first_name") or "").strip()
            or str(user.get("username") or "").strip()
            or "Foydalanuvchi"
        )
        if ft == "cv":
            log_cv(int(telegram_id), name)
        else:
            log_obyektivka(int(telegram_id), name)
        log_download(int(telegram_id), name, document=ft)
        admin_data.invalidate_metrics_cache()
    return data


def list_by_user(telegram_id: int, limit: int = 20) -> list[dict[str, Any]]:
    user = users_repo.get_by_telegram_id(telegram_id)
    if not user:
        return []
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT * FROM generated_files
            WHERE user_id = ? ORDER BY created_at DESC LIMIT ?
            """,
            (int(user["id"]), limit),
        ).fetchall()
    return [row_to_dict(r) for r in rows if r]


def list_all(limit: int = 50) -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT g.*, u.telegram_id, u.first_name
            FROM generated_files g
            JOIN users u ON u.id = g.user_id
            ORDER BY g.created_at DESC LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [row_to_dict(r) for r in rows if r]
