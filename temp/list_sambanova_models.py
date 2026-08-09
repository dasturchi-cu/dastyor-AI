"""List SambaNova models using first configured key."""
import asyncio
import json
import os

import httpx


async def main() -> None:
    raw = os.getenv("SAMBANOVA_API_KEYS") or os.getenv("SAMBANOVA_API_KEY") or ""
    key = raw.split(",")[0].strip()
    if not key:
        print("no key")
        return
    headers = {"Authorization": f"Bearer {key}"}
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get("https://api.sambanova.ai/v1/models", headers=headers)
        print("status", resp.status_code)
        if resp.status_code != 200:
            print(resp.text[:500])
            return
        data = resp.json()
        ids = [m.get("id") for m in data.get("data", []) if m.get("id")]
        print(json.dumps(ids[:30], indent=2))


if __name__ == "__main__":
    asyncio.run(main())
