"""Audit AI keys from .env — values are never printed."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv(".env")

from features.ai.routing.config import reload_routing_config

cfg = reload_routing_config()
print("=== CONFIGURED PROVIDERS ===")
for p, pc in sorted(cfg.providers.items(), key=lambda x: x[0].value):
    print(
        f"{p.value}: keys={len(pc.api_keys)} models={len(pc.models)} "
        f"primary_model={pc.models[0] if pc.models else '-'}"
    )
print(f"primary={cfg.primary_provider.value}")
print("fallback=", [x.value for x in cfg.fallback_order])

patterns = [
    "GEMINI",
    "OPENAI",
    "OPENROUTER",
    "GROQ",
    "CLOUDFLARE",
    "SAMBANOVA",
    "GITHUB",
    "GOOGLE_API",
]
print("\n=== ENV KEY VARS (counts only) ===")
for pat in patterns:
    found = [k for k in os.environ if pat in k and (os.environ.get(k) or "").strip()]
    if not found:
        continue
    print(pat, ":", len(found), "vars")
    for k in sorted(found):
        v = (os.environ[k] or "").strip()
        if k.endswith("_KEYS") or "," in v:
            n = len([x for x in v.split(",") if x.strip()])
            print(f"  {k} = {n} key(s)")
        else:
            print(f"  {k} = set (len {len(v)})")
