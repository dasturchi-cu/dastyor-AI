"""One key per provider — print actual API errors."""
import asyncio
import json

from features.ai.routing.adapters import generate_with_endpoint
from features.ai.routing.config import load_routing_config
from features.ai.routing.types import Endpoint


async def main() -> None:
    cfg = load_routing_config()
    rows = []
    for pname, pcfg in cfg.providers.items():
        if not pcfg.api_keys:
            continue
        ep = Endpoint(
            provider=pname,
            key_index=1,
            model=pcfg.models[0] if pcfg.models else "",
            api_key=pcfg.api_keys[0],
            extras=dict(pcfg.extras),
        )
        r = await generate_with_endpoint(ep, "Reply with exactly: OK", timeout_sec=20.0)
        rows.append(
            {
                "provider": pname.value,
                "model": ep.model,
                "ok": bool(r.text and not r.error),
                "text": (r.text or "")[:80],
                "error": r.error,
                "ms": r.response_time_ms,
            }
        )
    print(json.dumps(rows))


if __name__ == "__main__":
    asyncio.run(main())
