"""Admin panel action implementations."""
from __future__ import annotations

import logging
from pathlib import Path

from aiogram.fsm.context import FSMContext
from aiogram.types import FSInputFile, Message

from config.settings import settings
from database.repositories import activity as activity_repo
from database.repositories import admin_stats as stats_repo
from database.repositories import error_logs as error_logs_repo
from database.repositories import generated_files as files_repo
from database.repositories import payments as payments_repo
from features.admin import service as admin_service
from features.admin.dashboard import build_dashboard_text, start_dashboard
from features.admin.formatters import (
    build_payments_list_text,
    build_statistics_text,
    build_top_users_report,
    build_users_list_text,
)
from features.admin.keyboards import (
    error_filter_kb,
    export_kb,
    payment_filter_kb,
    user_profile_kb,
)
from features.admin.states import AdminStates
from shared.keyboards import admin_menu, user_menu
from shared.payment_notifications import (
    build_payment_notification_text,
    build_pending_payments_list,
)
from shared.payment_test_filter import filter_real_users, is_test_payment

logger = logging.getLogger(__name__)


async def handle_users(message: Message, state: FSMContext) -> None:
    await state.clear()
    rows = await _run_sync(stats_repo.list_users_enriched, 200)
    rows = filter_real_users(rows)[:20]
    total = await _run_sync(stats_repo.count_real_users)
    text = build_users_list_text(rows, total=total)
    await message.answer(text, reply_markup=admin_menu())


async def handle_search_prompt(message: Message, state: FSMContext) -> None:
    await state.set_state(AdminStates.user_search)
    await message.answer(
        "🔍 Qidirish\n\n@username, user_id yoki ism kiriting.",
        reply_markup=admin_menu(),
    )


async def handle_stats(message: Message, state: FSMContext) -> None:
    await state.clear()
    metrics = await _run_sync(stats_repo.dashboard_snapshot)
    text = build_statistics_text(metrics)
    await message.answer(text, reply_markup=admin_menu())


async def handle_top(message: Message, state: FSMContext) -> None:
    await state.clear()
    report = await _run_sync(stats_repo.top_users_report, 10)
    for key in ("by_purchases", "by_documents", "by_activity"):
        if key in report:
            report[key] = filter_real_users(report[key])
    text = build_top_users_report(report)
    await message.answer(text, reply_markup=admin_menu())


async def handle_broadcast_prompt(message: Message, state: FSMContext) -> None:
    await state.set_state(AdminStates.broadcast_text)
    await message.answer(
        "📢 Barcha foydalanuvchilarga yuboriladigan xabar matnini yozing:",
        reply_markup=admin_menu(),
    )


async def handle_export_menu(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("📥 Export — faylni tanlang:", reply_markup=export_kb())


async def handle_errors(message: Message, state: FSMContext) -> None:
    await state.clear()
    rows = await _run_sync(error_logs_repo.list_recent, 20)
    await message.answer(
        admin_service.build_error_log_text(rows),
        reply_markup=error_filter_kb(),
    )


async def handle_payments_menu(message: Message, state: FSMContext) -> None:
    await state.clear()
    rows = await _run_sync(stats_repo.list_payments_enriched, limit=15)
    text = build_payments_list_text(rows, title="Oxirgi to'lovlar")
    await message.answer(text, reply_markup=payment_filter_kb())


async def handle_pending_payments(message: Message, state: FSMContext) -> None:
    await state.clear()
    rows = await _run_sync(stats_repo.list_payments_enriched, status="PENDING", limit=15)
    rows = [r for r in rows if not is_test_payment(r)]
    if not rows:
        await message.answer("📥 Kutilayotgan to'lovlar yo'q.", reply_markup=admin_menu())
        return
    text = build_payments_list_text(rows, title="Kutilayotgan to'lovlar")
    await message.answer(text, reply_markup=admin_menu())
    await _send_payment_rows(message, rows)


async def handle_files(message: Message, state: FSMContext) -> None:
    await state.clear()
    rows = await _run_sync(files_repo.list_all, 20)
    if not rows:
        await message.answer("📁 Yaratilgan fayllar yo'q.", reply_markup=admin_menu())
        return
    lines = ["<b>📁 Hujjatlar (oxirgi 20)</b>\n"]
    for f in rows:
        lines.append(
            f"• #{f['id']} {f['file_type']} — <code>{f.get('telegram_id')}</code> "
            f"— {f.get('file_name') or '—'}"
        )
    await message.answer("\n".join(lines), reply_markup=admin_menu())


async def handle_activity(message: Message, state: FSMContext) -> None:
    await state.clear()
    rows = await _run_sync(activity_repo.list_recent, 15)
    if not rows:
        await message.answer("🔥 Hozircha faollik yo'q.", reply_markup=admin_menu())
        return
    from features.admin.dashboard import _feed_line

    lines = ["<b>🔥 Jonli faollik</b>\n"]
    for ev in rows:
        lines.append(f"• {_feed_line(ev)}")
    await message.answer("\n".join(lines), reply_markup=admin_menu())


async def handle_settings(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        "<b>⚙️ Sozlamalar</b>\n\n"
        f"Narx: <b>{settings.single_doc_price_uzs:,} so'm</b>\n"
        f"Karta: <code>{settings.payment_card_number}</code>\n"
        f"Egasi: {settings.payment_card_owner}\n"
        f"Avto-tasdiq: <b>{'yoqilgan' if settings.auto_approve_payments else 'o\'chirilgan'}</b>\n"
        f"Admin guruh: <code>{settings.premium_admin_group_id}</code>\n"
        f"Support guruh: <code>{settings.support_group_id}</code>\n"
        f"Dashboard yangilanish: <b>{settings.admin_dashboard_refresh_sec}s</b>",
        reply_markup=admin_menu(),
    )


async def handle_dashboard_refresh(message: Message, state: FSMContext) -> None:
    await state.clear()
    if not message.from_user:
        return
    await start_dashboard(
        message.bot,
        admin_id=message.from_user.id,
        chat_id=message.chat.id,
    )
    await message.answer("🔄 Dashboard yangilandi.", reply_markup=admin_menu())


async def handle_close(message: Message, state: FSMContext) -> None:
    from features.admin.dashboard import stop_dashboard

    if message.from_user:
        stop_dashboard(message.from_user.id)
    await state.clear()
    await message.answer("Admin panel yopildi.", reply_markup=user_menu())


async def _send_payment_rows(message: Message, rows: list[dict]) -> None:
    rows = [p for p in rows if not is_test_payment(p)]
    summary = build_pending_payments_list(rows[:10])
    if summary:
        await message.answer(summary)
    for p in rows[:10]:
        pid = int(p["id"])
        purchase_number = await _run_sync(
            payments_repo.count_user_payments, int(p.get("user_id") or 0)
        )
        kind = str(p.get("document_type") or "manual")
        text = build_payment_notification_text(
            p,
            kind=kind,
            purchase_number=purchase_number,
        )
        receipt = p.get("receipt_path")
        st = str(p.get("status") or "").upper()
        from shared.keyboards import payment_review_kb

        kb = payment_review_kb(pid) if st == "PENDING" else None
        if receipt and Path(receipt).is_file():
            await message.answer_photo(FSInputFile(receipt), caption=text, reply_markup=kb)
        else:
            await message.answer(text, reply_markup=kb)


async def _run_sync(fn, *args, **kwargs):
    import asyncio

    return await asyncio.to_thread(fn, *args, **kwargs)
