"""AI routing request logs and analytics."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from database.connection import get_connection, row_to_dict
from features.ai.routing.cooldown import get_cooldown_registry
from features.ai.routing.config import load_routing_config
from features.ai.routing.pool import get_endpoint_pool
from features.ai.routing.types import DashboardSnapshot, ProviderStats

# Rough USD per 1M tokens for cost estimation (input+output blended)
_COST_PER_M_TOKEN: dict[str, float] = {
    "gemini": 0.15,
    "openai": 0.60,
    "openrouter": 0.40,
    "groq": 0.05,
    "cloudflare": 0.01,
}


def log_request(
    *,
    provider: str,
    key_index: int,
    model: str,
    request_time: str,
    response_time_ms: int | None,
    status: str,
    error: str | None = None,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    total_tokens: int = 0,
) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO ai_request_logs (
                provider, key_index, model, request_time, response_time_ms,
                status, error, prompt_tokens, completion_tokens, total_tokens
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                provider,
                key_index,
                model,
                request_time,
                response_time_ms,
                status,
                (error or "")[:2000] or None,
                prompt_tokens,
                completion_tokens,
                total_tokens or (prompt_tokens + completion_tokens),
            ),
        )


def _today_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _hour_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H")


def get_provider_stats() -> list[dict[str, Any]]:
    today = _today_utc()
    hour = _hour_utc()
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT
                provider,
                SUM(CASE WHEN substr(request_time, 1, 10) = ? THEN 1 ELSE 0 END) AS requests_today,
                SUM(CASE WHEN substr(request_time, 1, 13) = ? THEN 1 ELSE 0 END) AS requests_hour,
                SUM(CASE WHEN substr(request_time, 1, 10) = ? THEN COALESCE(total_tokens, 0) ELSE 0 END) AS tokens_used,
                SUM(CASE WHEN status IN ('failover', 'error') AND substr(request_time, 1, 10) = ? THEN 1 ELSE 0 END) AS failures,
                SUM(CASE WHEN status = 'failover' AND substr(request_time, 1, 10) = ?
                    AND (error LIKE '%429%' OR error LIKE '%rate%') THEN 1 ELSE 0 END) AS rate_limits,
                SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) AS successes,
                COUNT(*) AS total_all
            FROM ai_request_logs
            GROUP BY provider
            """,
            (today, hour, today, today, today),
        ).fetchall()

    out: list[dict[str, Any]] = []
    for row in rows:
        d = row_to_dict(row) or {}
        total = int(d.get("total_all") or 0)
        successes = int(d.get("successes") or 0)
        success_rate = (successes / total * 100.0) if total else 100.0
        d["success_rate"] = round(success_rate, 1)
        d["health_pct"] = round(success_rate, 1)
        out.append(d)
    return out


def get_top_provider_model() -> tuple[str | None, str | None]:
    with get_connection() as conn:
        prow = conn.execute(
            """
            SELECT provider, COUNT(*) AS c FROM ai_request_logs
            WHERE substr(request_time, 1, 10) = date('now')
            GROUP BY provider ORDER BY c DESC LIMIT 1
            """
        ).fetchone()
        mrow = conn.execute(
            """
            SELECT model, COUNT(*) AS c FROM ai_request_logs
            WHERE substr(request_time, 1, 10) = date('now')
            GROUP BY model ORDER BY c DESC LIMIT 1
            """
        ).fetchone()
    top_p = str(prow["provider"]) if prow else None
    top_m = str(mrow["model"]) if mrow else None
    return top_p, top_m


def get_failure_rate_today() -> float:
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN status IN ('failover', 'error') THEN 1 ELSE 0 END) AS fails
            FROM ai_request_logs
            WHERE substr(request_time, 1, 10) = date('now')
            """
        ).fetchone()
    if not row or not int(row["total"]):
        return 0.0
    return round(int(row["fails"] or 0) / int(row["total"]) * 100.0, 2)


def estimate_cost_today() -> float:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT provider, SUM(COALESCE(total_tokens, 0)) AS tokens
            FROM ai_request_logs
            WHERE date(request_time) = date('now')
            GROUP BY provider
            """
        ).fetchall()
    cost = 0.0
    for row in rows:
        prov = str(row["provider"])
        tokens = int(row["tokens"] or 0)
        rate = _COST_PER_M_TOKEN.get(prov, 0.20)
        cost += tokens / 1_000_000.0 * rate
    return round(cost, 4)


def get_dashboard_snapshot() -> DashboardSnapshot:
    cfg = load_routing_config()
    pool = get_endpoint_pool()
    cooldown = get_cooldown_registry(cfg.cooldown_ms)
    active = pool.get_active_route()

    raw_stats = get_provider_stats()
    cooldowns = cooldown.list_active()
    cooling_set = {(c["provider"], c["key_index"]) for c in cooldowns}

    providers: list[ProviderStats] = []
    for pname in cfg.providers:
        match = next((s for s in raw_stats if s.get("provider") == pname.value), None)
        in_cd = any(c["provider"] == pname.value for c in cooldowns)
        cd_until = next(
            (c["until"] for c in cooldowns if c["provider"] == pname.value),
            None,
        )
        providers.append(
            ProviderStats(
                provider=pname.value,
                requests_today=int(match.get("requests_today") or 0) if match else 0,
                requests_hour=int(match.get("requests_hour") or 0) if match else 0,
                tokens_used=int(match.get("tokens_used") or 0) if match else 0,
                failures=int(match.get("failures") or 0) if match else 0,
                rate_limits=int(match.get("rate_limits") or 0) if match else 0,
                success_rate=float(match.get("success_rate") or 100.0) if match else 100.0,
                health_pct=float(match.get("health_pct") or 100.0) if match else 100.0,
                in_cooldown=in_cd,
                cooldown_until=cd_until,
            )
        )

    top_p, top_m = get_top_provider_model()

    with get_connection() as conn:
        totals = conn.execute(
            """
            SELECT COUNT(*) AS reqs, SUM(COALESCE(total_tokens,0)) AS tokens
            FROM ai_request_logs WHERE date(request_time) = date('now')
            """
        ).fetchone()

    # Mark active key cooldown
    active_status = active.status
    if cooling_set and (active.provider.value, active.key_index) in cooling_set:
        active_status = "COOLDOWN"

    active_copy = active
    active_copy.status = active_status

    return DashboardSnapshot(
        active=active_copy,
        providers=providers,
        top_provider=top_p,
        top_model=top_m,
        failure_rate_pct=get_failure_rate_today(),
        estimated_cost_usd=estimate_cost_today(),
        total_requests_today=int(totals["reqs"] or 0) if totals else 0,
        total_tokens_today=int(totals["tokens"] or 0) if totals else 0,
        cooldowns=cooldowns,
    )


def snapshot_to_dict() -> dict[str, Any]:
    snap = get_dashboard_snapshot()
    return {
        "active": {
            "provider": snap.active.provider.value,
            "key_index": snap.active.key_index,
            "model": snap.active.model,
            "status": snap.active.status,
            "health_pct": round(snap.active.health_pct, 1),
            "updated_at": snap.active.updated_at,
        },
        "providers": [
            {
                "provider": p.provider,
                "requests_today": p.requests_today,
                "requests_hour": p.requests_hour,
                "tokens_used": p.tokens_used,
                "failures": p.failures,
                "rate_limits": p.rate_limits,
                "health_pct": round(p.health_pct, 1),
                "in_cooldown": p.in_cooldown,
                "cooldown_until": p.cooldown_until,
            }
            for p in snap.providers
        ],
        "analytics": {
            "top_provider": snap.top_provider,
            "top_model": snap.top_model,
            "failure_rate_pct": snap.failure_rate_pct,
            "estimated_cost_usd": snap.estimated_cost_usd,
            "total_requests_today": snap.total_requests_today,
            "total_tokens_today": snap.total_tokens_today,
        },
        "cooldowns": snap.cooldowns,
    }
