"""Direct Gemini REST calls (per-request API key, thinking disabled on 2.5 Flash).

The legacy google-generativeai SDK keeps the API key in global state, so concurrent
requests with different keys race each other, and it cannot turn off 2.5 Flash
"thinking" — those hidden thinking tokens are billed as output and were the bulk
of the per-request cost for simple translate/extract prompts.
"""
from __future__ import annotations

import base64
import os
from dataclasses import dataclass
from typing import Any

import httpx

from shared.ai_errors import AiQuotaError

_API_BASE = "https://generativelanguage.googleapis.com/v1beta"


@dataclass
class GeminiResult:
    text: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    block_reason: str = ""


def _thinking_config(model: str) -> dict[str, Any] | None:
    # 2.5 Flash / Flash-Lite accept thinkingBudget=0; 2.5 Pro and Gemini 3 do not.
    if "2.5-flash" in (model or ""):
        return {"thinkingBudget": int(os.getenv("GEMINI_THINKING_BUDGET", "0") or 0)}
    return None


def text_part(text: str) -> dict[str, Any]:
    return {"text": text}


def inline_part(data: bytes, mime_type: str) -> dict[str, Any]:
    return {"inlineData": {"mimeType": mime_type, "data": base64.b64encode(data).decode("ascii")}}


async def generate_content(
    api_key: str,
    model: str,
    parts: list[dict[str, Any]] | str,
    *,
    timeout_sec: float,
    temperature: float | None = None,
    max_output_tokens: int | None = None,
    response_mime_type: str | None = None,
) -> GeminiResult:
    """One generateContent call. Raises AiQuotaError on 429, RuntimeError on HTTP errors."""
    if isinstance(parts, str):
        parts = [text_part(parts)]

    gen_cfg: dict[str, Any] = {}
    thinking = _thinking_config(model)
    if thinking is not None:
        gen_cfg["thinkingConfig"] = thinking
    if temperature is not None:
        gen_cfg["temperature"] = temperature
    if max_output_tokens:
        gen_cfg["maxOutputTokens"] = int(max_output_tokens)
    if response_mime_type:
        gen_cfg["responseMimeType"] = response_mime_type

    body: dict[str, Any] = {"contents": [{"role": "user", "parts": parts}]}
    if gen_cfg:
        body["generationConfig"] = gen_cfg

    url = f"{_API_BASE}/models/{model}:generateContent"
    async with httpx.AsyncClient(timeout=httpx.Timeout(timeout_sec)) as client:
        resp = await client.post(url, json=body, headers={"x-goog-api-key": api_key})

    if resp.status_code == 429:
        raise AiQuotaError(f"429 quota: {resp.text[:200]}")
    if resp.status_code >= 400:
        raise RuntimeError(f"Gemini {resp.status_code} model={model}: {resp.text[:200]}")

    data = resp.json()
    chunks: list[str] = []
    for cand in data.get("candidates") or []:
        for part in (cand.get("content") or {}).get("parts") or []:
            if part.get("thought"):
                continue
            t = part.get("text")
            if t:
                chunks.append(str(t))
        if chunks:
            break

    usage = data.get("usageMetadata") or {}
    prompt_tok = int(usage.get("promptTokenCount") or 0)
    completion_tok = int(usage.get("candidatesTokenCount") or 0) + int(
        usage.get("thoughtsTokenCount") or 0
    )
    return GeminiResult(
        text="".join(chunks).strip(),
        prompt_tokens=prompt_tok,
        completion_tokens=completion_tok,
        total_tokens=int(usage.get("totalTokenCount") or (prompt_tok + completion_tok)),
        block_reason=str((data.get("promptFeedback") or {}).get("blockReason") or ""),
    )
