"""Admin Telegram security dashboard."""
from __future__ import annotations

import html

from database.repositories import security_dashboard as sec_dash_repo


def build_security_dashboard_text(snapshot: dict) -> str:
    score = int(snapshot.get("security_score") or 0)
    if score >= 80:
        score_emoji = "🟢"
    elif score >= 60:
        score_emoji = "🟡"
    else:
        score_emoji = "🔴"

    lines = [
        "<b>🔒 XAVFSIZLIK DASHBOARD</b>",
        f"{score_emoji} Security Score: <b>{score}/100</b>",
        "",
        f"👥 Faol foydalanuvchilar: <b>{snapshot.get('active_users', 0)}</b>",
        f"🔑 Faol sessiyalar: <b>{snapshot.get('active_sessions', 0)}</b>",
        f"🚫 Bloklangan: <b>{snapshot.get('blocked_users', 0)}</b>",
        "",
        "<b>⚠️ 24 soat ichida</b>",
        f"❌ Muvaffaqiyatsiz login: <b>{snapshot.get('failed_logins_24h', 0)}</b>",
        f"⏱ Rate limit: <b>{snapshot.get('rate_limit_hits_24h', 0)}</b>",
        f"💳 To'lov fraud: <b>{snapshot.get('payment_fraud_24h', 0)}</b>",
        f"🤖 AI abuse: <b>{snapshot.get('ai_abuse_24h', 0)}</b>",
        f"📁 Fayl rad etilgan: <b>{snapshot.get('file_rejections_24h', 0)}</b>",
    ]

    suspicious = snapshot.get("suspicious_ips") or []
    if suspicious:
        lines.extend(["", "<b>🌐 Shubhali IP</b>"])
        for row in suspicious[:5]:
            ip = html.escape(str(row.get("ip") or "?"))
            hits = int(row.get("hits") or 0)
            lines.append(f"• <code>{ip}</code> — {hits} hodisa")

    events = snapshot.get("recent_events") or []
    if events:
        lines.extend(["", "<b>📋 So'nggi hodisalar</b>"])
        for ev in events[:5]:
            et = html.escape(str(ev.get("event_type") or ""))
            sev = html.escape(str(ev.get("severity") or ""))
            lines.append(f"• [{sev}] {et}")

    return "\n".join(lines)
