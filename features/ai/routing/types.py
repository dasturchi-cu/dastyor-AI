"""AI routing types."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ProviderName(str, Enum):
    GEMINI = "gemini"
    OPENAI = "openai"
    OPENROUTER = "openrouter"
    GROQ = "groq"
    CLOUDFLARE = "cloudflare"


class RequestStatus(str, Enum):
    SUCCESS = "success"
    FAILOVER = "failover"
    ERROR = "error"
    COOLDOWN = "cooldown"


@dataclass(frozen=True)
class ProviderConfig:
    name: ProviderName
    api_keys: tuple[str, ...]
    models: tuple[str, ...]
    extras: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class RoutingConfig:
    primary_provider: ProviderName
    fallback_order: tuple[ProviderName, ...]
    providers: dict[ProviderName, ProviderConfig]
    request_timeout_ms: int
    max_retries: int
    retry_delay_ms: int
    cooldown_ms: int


@dataclass
class Endpoint:
    """A single routable target: provider + key index + model."""

    provider: ProviderName
    key_index: int  # 1-based for display
    model: str
    api_key: str
    extras: dict[str, str] = field(default_factory=dict)
    health_score: float = 100.0
    weight: float = 1.0


@dataclass
class AttemptResult:
    text: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    response_time_ms: int = 0
    error: str | None = None


@dataclass
class ActiveRoute:
    provider: ProviderName
    key_index: int
    model: str
    status: str = "ACTIVE"
    health_pct: float = 100.0
    updated_at: str = ""


@dataclass
class ProviderStats:
    provider: str
    requests_today: int = 0
    requests_hour: int = 0
    tokens_used: int = 0
    failures: int = 0
    rate_limits: int = 0
    success_rate: float = 100.0
    health_pct: float = 100.0
    in_cooldown: bool = False
    cooldown_until: str | None = None


@dataclass
class DashboardSnapshot:
    active: ActiveRoute
    providers: list[ProviderStats]
    top_provider: str | None = None
    top_model: str | None = None
    failure_rate_pct: float = 0.0
    estimated_cost_usd: float = 0.0
    total_requests_today: int = 0
    total_tokens_today: int = 0
    cooldowns: list[dict[str, Any]] = field(default_factory=list)
