"""Load multi-provider AI routing configuration from environment."""
from __future__ import annotations

import os
import re
from functools import lru_cache

from features.ai.routing.types import ProviderName, ProviderConfig, RoutingConfig

_ENV = os.getenv


def _strip_bom(key: str) -> str:
    return (_ENV(key) or _ENV(f"\ufeff{key}") or "").strip()


def _parse_csv(raw: str) -> tuple[str, ...]:
    return tuple(v.strip() for v in raw.split(",") if v.strip())


def _collect_numbered_keys(prefix: str) -> list[str]:
    """Collect PREFIX, PREFIX_2, PREFIX_3, ... in numeric order."""
    keys: list[tuple[int, str]] = []
    primary = _strip_bom(prefix)
    if primary:
        keys.append((1, primary))
    pattern = re.compile(rf"^{re.escape(prefix)}_(\d+)$", re.IGNORECASE)
    for env_key, value in os.environ.items():
        m = pattern.match(env_key)
        if not m:
            continue
        val = (value or "").strip()
        if val:
            keys.append((int(m.group(1)), val))
    keys.sort(key=lambda x: x[0])
    # Deduplicate while preserving order
    seen: set[str] = set()
    out: list[str] = []
    for _, k in keys:
        if k not in seen:
            seen.add(k)
            out.append(k)
    return out


def _collect_api_keys(provider: ProviderName) -> tuple[str, ...]:
    plural = {
        ProviderName.GEMINI: "GEMINI_API_KEYS",
        ProviderName.OPENAI: "OPENAI_API_KEYS",
        ProviderName.OPENROUTER: "OPENROUTER_API_KEYS",
        ProviderName.GROQ: "GROQ_API_KEYS",
        ProviderName.CLOUDFLARE: "CLOUDFLARE_API_KEYS",
        ProviderName.SAMBANOVA: "SAMBANOVA_API_KEYS",
        ProviderName.GITHUB: "GITHUB_API_KEYS",
    }
    singular_prefix = {
        ProviderName.GEMINI: "GEMINI_API_KEY",
        ProviderName.OPENAI: "OPENAI_API_KEY",
        ProviderName.OPENROUTER: "OPENROUTER_API_KEY",
        ProviderName.GROQ: "GROQ_API_KEY",
        ProviderName.CLOUDFLARE: "CLOUDFLARE_API_TOKEN",
        ProviderName.SAMBANOVA: "SAMBANOVA_API_KEY",
        ProviderName.GITHUB: "GITHUB_API_KEY",
    }

    plural_raw = _strip_bom(plural[provider])
    if plural_raw:
        return _parse_csv(plural_raw)

    numbered = _collect_numbered_keys(singular_prefix[provider])
    if numbered:
        return tuple(numbered)

    if provider == ProviderName.GEMINI:
        legacy = _strip_bom("GOOGLE_API_KEY")
        if legacy:
            return (legacy,)

    if provider == ProviderName.CLOUDFLARE:
        token = _strip_bom("CLOUDFLARE_API_TOKEN")
        if token:
            return (token,)

    if provider == ProviderName.GITHUB:
        pat = _strip_bom("GITHUB_PERSONAL_ACCESS_TOKEN")
        if pat:
            return (pat,)

    return ()


def _collect_models(provider: ProviderName) -> tuple[str, ...]:
    primary_key = {
        ProviderName.GEMINI: "GEMINI_MODEL",
        ProviderName.OPENAI: "OPENAI_MODEL",
        ProviderName.OPENROUTER: "OPENROUTER_MODEL",
        ProviderName.GROQ: "GROQ_MODEL",
        ProviderName.CLOUDFLARE: "CLOUDFLARE_AI_MODEL",
        ProviderName.SAMBANOVA: "SAMBANOVA_MODEL",
        ProviderName.GITHUB: "GITHUB_MODEL",
    }
    fallback_key = {
        ProviderName.GEMINI: "GEMINI_MODEL_FALLBACKS",
        ProviderName.OPENAI: "OPENAI_MODEL_FALLBACKS",
        ProviderName.OPENROUTER: "OPENROUTER_MODEL_FALLBACKS",
        ProviderName.GROQ: "GROQ_MODEL_FALLBACKS",
        ProviderName.CLOUDFLARE: "CLOUDFLARE_AI_MODEL_FALLBACKS",
        ProviderName.SAMBANOVA: "SAMBANOVA_MODEL_FALLBACKS",
        ProviderName.GITHUB: "GITHUB_MODEL_FALLBACKS",
    }
    defaults = {
        ProviderName.GEMINI: ("gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash-latest"),
        ProviderName.OPENAI: ("gpt-4o-mini", "gpt-4o", "gpt-4.1-mini"),
        ProviderName.OPENROUTER: ("deepseek/deepseek-chat", "openai/gpt-4o-mini"),
        ProviderName.GROQ: ("llama-3.1-8b-instant", "llama-3.1-70b-versatile"),
        ProviderName.CLOUDFLARE: ("@cf/meta/llama-3.1-8b-instruct",),
        ProviderName.SAMBANOVA: (
            "DeepSeek-V3.1",
            "Meta-Llama-3.3-70B-Instruct",
            "gpt-oss-120b",
            "DeepSeek-V3.2",
        ),
        ProviderName.GITHUB: (
            "meta-llama-3.1-8b-instruct",
            "meta-llama-3.1-70b-instruct",
            "meta-llama-3.1-405b-instruct",
            "gpt-4o-mini",
            "gpt-4o",
            "cohere-command-r-plus",
            "mistral-large",
            "phi-3-medium-128k-instruct",
            "mistral-nemo",
            "cohere-command-r"
        ),
    }

    primary = _strip_bom(primary_key[provider])
    fallbacks = _parse_csv(_strip_bom(fallback_key[provider]))
    models: list[str] = []
    if primary:
        models.append(primary)
    for m in fallbacks:
        if m not in models:
            models.append(m)
    if not models:
        models = list(defaults[provider])
    return tuple(models)


def _provider_extras(provider: ProviderName) -> dict[str, str]:
    if provider == ProviderName.CLOUDFLARE:
        extras: dict[str, str] = {}
        account = _strip_bom("CLOUDFLARE_ACCOUNT_ID")
        if account:
            extras["account_id"] = account
        return extras
    if provider == ProviderName.OPENROUTER:
        extras = {}
        referer = _strip_bom("OPENROUTER_HTTP_REFERER")
        title = _strip_bom("OPENROUTER_X_TITLE")
        if referer:
            extras["http_referer"] = referer
        if title:
            extras["x_title"] = title
        return extras
    return {}


def _parse_provider_name(raw: str) -> ProviderName | None:
    try:
        return ProviderName(raw.strip().lower())
    except ValueError:
        return None


def _int_env(key: str, default: int) -> int:
    raw = _strip_bom(key)
    try:
        return int(raw) if raw else default
    except ValueError:
        return default


@lru_cache(maxsize=1)
def load_routing_config() -> RoutingConfig:
    primary_raw = _strip_bom("AI_PROVIDER") or "gemini"
    primary = _parse_provider_name(primary_raw) or ProviderName.GEMINI

    order_raw = _strip_bom("AI_FALLBACK_ORDER") or "sambanova,github,groq,cloudflare"
    fallback: list[ProviderName] = []
    for part in order_raw.split(","):
        p = _parse_provider_name(part)
        if p and p not in fallback and p != primary:
            fallback.append(p)

    default_order = [
        ProviderName.SAMBANOVA,
        ProviderName.GITHUB,
        ProviderName.GROQ,
        ProviderName.CLOUDFLARE,
    ]
    for p in default_order:
        if p not in fallback and p != primary:
            fallback.append(p)

    providers: dict[ProviderName, ProviderConfig] = {}
    for pname in ProviderName:
        keys = _collect_api_keys(pname)
        if not keys and pname not in (primary, *fallback):
            continue
        providers[pname] = ProviderConfig(
            name=pname,
            api_keys=keys,
            models=_collect_models(pname),
            extras=_provider_extras(pname),
        )

    cooldown_ms = _int_env("BOT_AI_COOLDOWN_MS", 0)
    if cooldown_ms <= 0:
        cooldown_ms = _int_env("AI_PROVIDER_COOLDOWN_MS", 900_000)  # 15 min default

    return RoutingConfig(
        primary_provider=primary,
        fallback_order=tuple(fallback),
        providers=providers,
        request_timeout_ms=_int_env("AI_REQUEST_TIMEOUT_MS", 90_000),
        max_retries=_int_env("AI_MAX_RETRIES", 2),
        retry_delay_ms=_int_env("AI_RETRY_DELAY_MS", 1500),
        cooldown_ms=cooldown_ms,
    )


def reload_routing_config() -> RoutingConfig:
    load_routing_config.cache_clear()
    return load_routing_config()
