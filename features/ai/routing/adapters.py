"""Provider HTTP/SDK adapters."""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

import httpx

from features.ai.routing.types import AttemptResult, Endpoint, ProviderName
from shared.ai_errors import AiQuotaError, is_failover_error, is_quota_error

logger = logging.getLogger(__name__)


def _message_content_to_text(content: Any) -> str:
    """Normalize chat completion `message.content` (str | list | None) to text."""
    if content is None:
        return ""
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                text = item.get("text")
                if text:
                    parts.append(str(text))
                elif item.get("type") == "text" and item.get("content"):
                    parts.append(str(item["content"]))
            else:
                text = getattr(item, "text", None)
                if text:
                    parts.append(str(text))
        return "".join(parts).strip()
    return str(content).strip()


async def _openai_compatible_chat(
    endpoint: Endpoint,
    prompt: str,
    *,
    base_url: str,
    extra_headers: dict[str, str] | None = None,
    timeout_sec: float,
) -> AttemptResult:
    headers = {
        "Authorization": f"Bearer {endpoint.api_key}",
        "Content-Type": "application/json",
    }
    if extra_headers:
        headers.update(extra_headers)

    payload = {
        "model": endpoint.model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
    }
    t0 = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(timeout_sec)) as client:
            resp = await client.post(f"{base_url.rstrip('/')}/chat/completions", json=payload, headers=headers)
            elapsed = int((time.perf_counter() - t0) * 1000)
            if resp.status_code == 429:
                raise AiQuotaError(f"429 rate limit: {resp.text[:200]}")
            if resp.status_code >= 500:
                raise RuntimeError(f"{resp.status_code} server error: {resp.text[:200]}")
            resp.raise_for_status()
            data = resp.json()
            message = (data.get("choices") or [{}])[0].get("message") or {}
            text = _message_content_to_text(message.get("content"))
            usage = data.get("usage") or {}
            return AttemptResult(
                text=text,
                prompt_tokens=int(usage.get("prompt_tokens") or 0),
                completion_tokens=int(usage.get("completion_tokens") or 0),
                total_tokens=int(usage.get("total_tokens") or 0),
                response_time_ms=elapsed,
            )
    except Exception as e:
        elapsed = int((time.perf_counter() - t0) * 1000)
        if is_quota_error(e):
            raise AiQuotaError(str(e)) from e
        if is_failover_error(e):
            raise
        return AttemptResult(response_time_ms=elapsed, error=str(e)[:500])


async def _gemini_generate(endpoint: Endpoint, prompt: str, *, timeout_sec: float) -> AttemptResult:
    import google.generativeai as genai

    t0 = time.perf_counter()
    try:
        genai.configure(api_key=endpoint.api_key)
        model = genai.GenerativeModel(endpoint.model)

        async def _call():
            return await model.generate_content_async(prompt)

        result = await asyncio.wait_for(_call(), timeout=timeout_sec)
        elapsed = int((time.perf_counter() - t0) * 1000)
        text = ""
        if result and getattr(result, "text", None):
            text = (result.text or "").strip()
        elif result and getattr(result, "candidates", None):
            for cand in result.candidates:
                parts = getattr(getattr(cand, "content", None), "parts", None) or []
                for part in parts:
                    t = getattr(part, "text", "") or ""
                    if t:
                        text += t
            text = text.strip()

        usage = getattr(result, "usage_metadata", None)
        prompt_tok = int(getattr(usage, "prompt_token_count", 0) or 0) if usage else 0
        completion_tok = int(getattr(usage, "candidates_token_count", 0) or 0) if usage else 0
        total_tok = int(getattr(usage, "total_token_count", 0) or 0) if usage else prompt_tok + completion_tok

        if not text:
            return AttemptResult(response_time_ms=elapsed, error="Empty Gemini response")

        return AttemptResult(
            text=text,
            prompt_tokens=prompt_tok,
            completion_tokens=completion_tok,
            total_tokens=total_tok,
            response_time_ms=elapsed,
        )
    except asyncio.TimeoutError as e:
        elapsed = int((time.perf_counter() - t0) * 1000)
        raise TimeoutError(f"Gemini timeout after {timeout_sec}s") from e
    except Exception as e:
        elapsed = int((time.perf_counter() - t0) * 1000)
        if is_quota_error(e):
            raise AiQuotaError(str(e)) from e
        if is_failover_error(e):
            raise
        return AttemptResult(response_time_ms=elapsed, error=str(e)[:500])


async def _cloudflare_generate(endpoint: Endpoint, prompt: str, *, timeout_sec: float) -> AttemptResult:
    account_id = endpoint.extras.get("account_id", "")
    if not account_id:
        return AttemptResult(error="CLOUDFLARE_ACCOUNT_ID missing")

    url = (
        f"https://api.cloudflare.com/client/v4/accounts/{account_id}"
        f"/ai/run/{endpoint.model}"
    )
    headers = {
        "Authorization": f"Bearer {endpoint.api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 1500,
        "max_decoding_tokens": 1500,
    }
    t0 = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(timeout_sec)) as client:
            resp = await client.post(url, json=payload, headers=headers)
            elapsed = int((time.perf_counter() - t0) * 1000)
            if resp.status_code == 429:
                raise AiQuotaError(f"429 rate limit: {resp.text[:200]}")
            if resp.status_code >= 500:
                raise RuntimeError(f"{resp.status_code}: {resp.text[:200]}")
            resp.raise_for_status()
            data = resp.json()
            result = data.get("result") or {}
            text = ""
            if isinstance(result, dict):
                raw = result.get("response") or result.get("text") or result.get("message")
                text = _message_content_to_text(raw)
            elif isinstance(result, str):
                text = result.strip()
            return AttemptResult(text=text, response_time_ms=elapsed)
    except Exception as e:
        elapsed = int((time.perf_counter() - t0) * 1000)
        if is_quota_error(e):
            raise AiQuotaError(str(e)) from e
        if is_failover_error(e):
            raise
        return AttemptResult(response_time_ms=elapsed, error=str(e)[:500])


async def generate_with_endpoint(
    endpoint: Endpoint,
    prompt: str,
    *,
    timeout_sec: float,
) -> AttemptResult:
    if endpoint.provider == ProviderName.GEMINI:
        return await _gemini_generate(endpoint, prompt, timeout_sec=timeout_sec)

    if endpoint.provider == ProviderName.OPENAI:
        return await _openai_compatible_chat(
            endpoint,
            prompt,
            base_url="https://api.openai.com/v1",
            timeout_sec=timeout_sec,
        )

    if endpoint.provider == ProviderName.SAMBANOVA:
        return await _openai_compatible_chat(
            endpoint,
            prompt,
            base_url="https://api.sambanova.ai/v1",
            timeout_sec=timeout_sec,
        )

    if endpoint.provider == ProviderName.GITHUB:
        return await _openai_compatible_chat(
            endpoint,
            prompt,
            base_url="https://models.inference.ai.azure.com",
            timeout_sec=timeout_sec,
        )

    if endpoint.provider == ProviderName.OPENROUTER:
        extra: dict[str, str] = {}
        if endpoint.extras.get("http_referer"):
            extra["HTTP-Referer"] = endpoint.extras["http_referer"]
        if endpoint.extras.get("x_title"):
            extra["X-Title"] = endpoint.extras["x_title"]
        return await _openai_compatible_chat(
            endpoint,
            prompt,
            base_url="https://openrouter.ai/api/v1",
            extra_headers=extra,
            timeout_sec=timeout_sec,
        )

    if endpoint.provider == ProviderName.GROQ:
        return await _openai_compatible_chat(
            endpoint,
            prompt,
            base_url="https://api.groq.com/openai/v1",
            timeout_sec=timeout_sec,
        )

    if endpoint.provider == ProviderName.CLOUDFLARE:
        return await _cloudflare_generate(endpoint, prompt, timeout_sec=timeout_sec)

    return AttemptResult(error=f"Unknown provider: {endpoint.provider}")


async def probe_endpoint(endpoint: Endpoint, *, timeout_sec: float = 15.0) -> tuple[bool, str | None]:
    """Lightweight health probe. Returns (ok, error_message)."""
    try:
        result = await generate_with_endpoint(
            endpoint,
            "Reply with exactly: OK",
            timeout_sec=timeout_sec,
        )
        if result.text and not result.error:
            return True, None
        return False, (result.error or "empty_response")[:200]
    except Exception as e:
        logger.debug(
            "Probe failed %s key#%s %s: %s",
            endpoint.provider.value,
            endpoint.key_index,
            endpoint.model,
            e,
        )
        return False, str(e)[:200]
