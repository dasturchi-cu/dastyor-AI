"""Admin Telegram — AI routing holati (faqat admin)."""
from __future__ import annotations

import html

from database.repositories.ai_routing import snapshot_to_dict


def fetch_ai_snapshot() -> dict:
    return snapshot_to_dict()


def _status_emoji(status: str) -> str:
    s = (status or "").upper()
    if s == "ACTIVE":
        return "🟢"
    if s == "COOLDOWN":
        return "🟡"
    return "⚪"


def build_ai_status_text(snapshot: dict, *, compact: bool = False) -> str:
    """Telegram HTML — joriy provider, kalit, model, health."""
    active = snapshot.get("active") or {}
    analytics = snapshot.get("analytics") or {}
    provider = html.escape(str(active.get("provider") or "—").upper())
    key_idx = int(active.get("key_index") or 0)
    model = html.escape(str(active.get("model") or "—"))
    status = str(active.get("status") or "IDLE")
    health = float(active.get("health_pct") or 100.0)
    emoji = _status_emoji(status)

    lines = [
        "<b>🤖 AI ROUTING</b>",
        f"{emoji} Holat: <b>{html.escape(status)}</b>",
        f"Provider: <b>{provider}</b>",
        f"Kalit: <b>#{key_idx or '—'}</b>",
        f"Model: <code>{model}</code>",
        f"Health: <b>{health:.0f}%</b>",
    ]

    if compact:
        reqs = int(analytics.get("total_requests_today") or 0)
        fail = float(analytics.get("failure_rate_pct") or 0)
        lines.append(f"Bugun: <b>{reqs}</b> so'rov | xato <b>{fail}%</b>")
        return "\n".join(lines)

    lines.extend(
        [
            "",
            "<b>📊 Bugun</b>",
            f"So'rovlar: <b>{int(analytics.get('total_requests_today') or 0)}</b>",
            f"Tokenlar: <b>{int(analytics.get('total_tokens_today') or 0):,}</b>",
            f"Xato foizi: <b>{float(analytics.get('failure_rate_pct') or 0)}%</b>",
            f"Taxminiy narx: <b>${float(analytics.get('estimated_cost_usd') or 0):.4f}</b>",
        ]
    )

    top_p = analytics.get("top_provider")
    top_m = analytics.get("top_model")
    if top_p or top_m:
        lines.extend(
            [
                "",
                "<b>🏆 Eng ko'p ishlatilgan</b>",
                f"Provider: <b>{html.escape(str(top_p or '—'))}</b>",
                f"Model: <code>{html.escape(str(top_m or '—'))}</code>",
            ]
        )

    providers = snapshot.get("providers") or []
    if providers:
        lines.extend(["", "<b>📡 Providerlar</b>"])
        for p in providers:
            name = html.escape(str(p.get("provider") or "").upper())
            if not name:
                continue
            hp = float(p.get("health_pct") or 100)
            reqs = int(p.get("requests_today") or 0)
            cd = " 🟡" if p.get("in_cooldown") else ""
            lines.append(f"• {name}{cd} — {reqs} so'rov, {hp:.0f}%")

    cooldowns = snapshot.get("cooldowns") or []
    if cooldowns:
        lines.extend(["", "<b>⏳ Cooldown</b>"])
        for c in cooldowns[:5]:
            prov = html.escape(str(c.get("provider") or ""))
            ki = int(c.get("key_index") or 0)
            rem = int(c.get("remaining_sec") or 0)
            lines.append(f"• {prov} #{ki} — {rem}s qoldi")

    from config.settings import settings

    base = (settings.site_base_url or "").rstrip("/")
    if base.startswith("https://"):
        lines.extend(
            [
                "",
                f"<i>To'liq web monitor: {html.escape(base)}/admin/ai-monitor</i>",
            ]
        )

    return "\n".join(lines)
