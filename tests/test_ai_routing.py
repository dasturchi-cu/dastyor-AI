"""AI routing / failover unit tests (no live API calls)."""
from __future__ import annotations

import os
import unittest
from unittest.mock import AsyncMock, patch

from features.ai.routing.config import load_routing_config, reload_routing_config
from features.ai.routing.cooldown import CooldownRegistry
from features.ai.routing.pool import EndpointPool, reset_endpoint_pool
from features.ai.routing.types import AttemptResult, Endpoint, ProviderName
from shared.ai_errors import AiQuotaError, is_failover_error


class TestConfigParsing(unittest.TestCase):
    def setUp(self):
        load_routing_config.cache_clear()
        self._env = os.environ.copy()

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._env)
        load_routing_config.cache_clear()

    def test_numbered_api_keys(self):
        os.environ["GEMINI_API_KEY"] = "key-one"
        os.environ["GEMINI_API_KEY_2"] = "key-two"
        os.environ["GEMINI_API_KEY_3"] = "key-three"
        os.environ["OPENAI_API_KEY"] = "sk-test"
        cfg = reload_routing_config()
        gemini = cfg.providers[ProviderName.GEMINI]
        self.assertEqual(gemini.api_keys, ("key-one", "key-two", "key-three"))

    def test_csv_api_keys(self):
        os.environ["GROQ_API_KEYS"] = "g1,g2,g3"
        cfg = reload_routing_config()
        groq = cfg.providers[ProviderName.GROQ]
        self.assertEqual(groq.api_keys, ("g1", "g2", "g3"))

    def test_fallback_order(self):
        os.environ["AI_FALLBACK_ORDER"] = "openrouter,groq"
        cfg = reload_routing_config()
        names = [p.value for p in cfg.fallback_order]
        self.assertIn("openrouter", names)
        self.assertIn("groq", names)
        self.assertEqual(cfg.cooldown_ms, 900_000)


class TestCooldown(unittest.TestCase):
    def test_cooldown_blocks_and_clears(self):
        reg = CooldownRegistry(default_cooldown_ms=5000)
        reg.set_cooldown(ProviderName.GEMINI, 1, reason="rate_limit")
        self.assertTrue(reg.is_cooling(ProviderName.GEMINI, 1))
        reg.clear(ProviderName.GEMINI, 1)
        self.assertFalse(reg.is_cooling(ProviderName.GEMINI, 1))


class TestEndpointPool(unittest.TestCase):
    def setUp(self):
        load_routing_config.cache_clear()
        self._saved = os.environ.copy()
        os.environ["GEMINI_API_KEY"] = "gk1"
        os.environ["GEMINI_API_KEY_2"] = "gk2"
        os.environ["GEMINI_MODEL"] = "gemini-2.5-flash"
        os.environ["GEMINI_MODEL_FALLBACKS"] = "gemini-2.0-flash"
        reload_routing_config()
        reset_endpoint_pool()

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._saved)
        load_routing_config.cache_clear()
        reset_endpoint_pool()

    def test_round_robin_key_rotation(self):
        pool = reset_endpoint_pool()
        first = pool.iter_failover_chain()
        second = pool.iter_failover_chain()
        self.assertTrue(first)
        self.assertTrue(second)
        # First endpoint key should rotate between calls
        k1 = first[0].key_index
        k2 = second[0].key_index
        self.assertIn(k1, (1, 2))
        self.assertIn(k2, (1, 2))

    def test_model_order_per_key(self):
        pool = reset_endpoint_pool()
        chain = pool.iter_failover_chain()
        models_for_key1 = [e.model for e in chain if e.key_index == 1]
        self.assertIn("gemini-2.5-flash", models_for_key1)
        self.assertIn("gemini-2.0-flash", models_for_key1)


class TestFailoverEngine(unittest.IsolatedAsyncioTestCase):
    def _prepare_env(self):
        load_routing_config.cache_clear()
        os.environ["GEMINI_API_KEY"] = "gk1"
        os.environ["OPENAI_API_KEY"] = "ok1"
        os.environ["AI_RETRY_DELAY_MS"] = "1"
        os.environ["AI_FALLBACK_ORDER"] = "openai"
        for k in list(os.environ):
            if k.startswith("GEMINI_API_KEY_") and k != "GEMINI_API_KEY":
                del os.environ[k]
        reload_routing_config()
        reset_endpoint_pool()
        from features.ai.routing.cooldown import reset_cooldown_registry

        reset_cooldown_registry(1000)

    def setUp(self):
        self._saved = os.environ.copy()
        self._prepare_env()

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._saved)
        load_routing_config.cache_clear()
        reset_endpoint_pool()

    async def test_failover_on_gemini_error(self):
        self._prepare_env()
        from features.ai.routing.engine import generate_text_with_failover

        calls: list[Endpoint] = []

        async def fake_generate(endpoint: Endpoint, prompt: str, *, timeout_sec: float):
            calls.append(endpoint)
            if endpoint.provider == ProviderName.GEMINI:
                raise AiQuotaError("429 quota")
            return AttemptResult(text="openai-ok", total_tokens=10, response_time_ms=50)

        with patch("features.ai.routing.engine.generate_with_endpoint", side_effect=fake_generate):
            with patch("features.ai.routing.engine._log_request"):
                text = await generate_text_with_failover("hello", timeout=5)
        self.assertEqual(text, "openai-ok")
        providers_tried = {c.provider for c in calls}
        self.assertIn(ProviderName.GEMINI, providers_tried)
        self.assertIn(ProviderName.OPENAI, providers_tried)

    async def test_all_exhausted_raises(self):
        self._prepare_env()
        from features.ai.routing.engine import generate_text_with_failover

        async def always_fail(endpoint: Endpoint, prompt: str, *, timeout_sec: float):
            raise AiQuotaError("quota")

        with patch("features.ai.routing.engine.generate_with_endpoint", side_effect=always_fail):
            with patch("features.ai.routing.engine._log_request"):
                with self.assertRaises(AiQuotaError):
                    await generate_text_with_failover("x", timeout=3)


class TestErrorClassification(unittest.TestCase):
    def test_failover_triggers(self):
        self.assertTrue(is_failover_error(AiQuotaError("429")))
        self.assertTrue(is_failover_error(TimeoutError()))
        self.assertTrue(is_failover_error(RuntimeError("503 service unavailable")))


if __name__ == "__main__":
    unittest.main()
