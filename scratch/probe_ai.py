import asyncio
import os
import sys
import ssl
from pathlib import Path

# Bypass SSL certificate verification globally for local testing
ssl._create_default_https_context = ssl._create_unverified_context

# Add project root to sys.path
root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))

# Load .env
from dotenv import load_dotenv
load_dotenv(dotenv_path=root / '.env')

from features.ai.routing.config import load_routing_config
from features.ai.routing.pool import get_endpoint_pool
from features.ai.routing.adapters import generate_with_endpoint

async def main():
    cfg = load_routing_config()
    print("AI Providers config:")
    print("Primary:", cfg.primary_provider)
    print("Fallback order:", cfg.fallback_order)
    
    pool = get_endpoint_pool()
    chain = pool.iter_failover_chain()
    
    if not chain:
        print("No endpoints found!")
        return

    # Filter to get only ONE representative endpoint per provider
    seen_providers = set()
    filtered_chain = []
    for ep in chain:
        if ep.provider not in seen_providers:
            seen_providers.add(ep.provider)
            filtered_chain.append(ep)

    print(f"\nProbing {len(filtered_chain)} unique providers (SSL Verification Bypassed):")
    for ep in filtered_chain:
        print(f"\n--- Probing Provider: {ep.provider.value} | Model: {ep.model} ---")
        try:
            result = await generate_with_endpoint(ep, "Say OK", timeout_sec=8.0)
            if result.error:
                print(f"[FAIL] Error: {result.error}")
            else:
                print(f"[OK] Success! Response: {result.text} (Time: {result.response_time_ms}ms)")
        except Exception as e:
            print(f"[FAIL] Exception: {type(e).__name__}: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())
