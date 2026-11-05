"""Shared Chromium pool: no recycling under in-flight renders, idle shutdown."""
from __future__ import annotations

import asyncio
import unittest
from unittest.mock import patch

from backend.services import render_service as rs


class _FakePage:
    async def emulate_media(self, **_):
        pass

    async def set_content(self, *_a, **_k):
        await asyncio.sleep(0.01)

    async def evaluate(self, *_a):
        pass

    async def wait_for_timeout(self, *_a):
        pass

    async def pdf(self, **_):
        return b"%PDF-fake"

    async def close(self):
        pass


class _FakeBrowser:
    def __init__(self):
        self.closed = False
        self.open_pages = 0
        self.closed_with_open_pages = False

    def is_connected(self):
        return not self.closed

    async def new_page(self):
        if self.closed:
            raise RuntimeError("Target closed")
        self.open_pages += 1
        browser = self

        class _Page(_FakePage):
            async def close(self):
                browser.open_pages -= 1

        return _Page()

    async def close(self):
        if self.open_pages:
            self.closed_with_open_pages = True
        self.closed = True


class _FakeManager:
    launched: list[_FakeBrowser] = []

    def __init__(self):
        self.chromium = self
        self.stopped = False

    async def start(self):
        return self

    async def launch(self, **_):
        b = _FakeBrowser()
        _FakeManager.launched.append(b)
        return b

    async def stop(self):
        self.stopped = True


class TestPlaywrightPool(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        _FakeManager.launched = []
        rs._pw_browser = None
        rs._pw_manager = None
        rs._pw_browser_uses = 0
        rs._pw_active_renders = 0
        rs._pw_idle_task = None
        rs._pw_browser_lock = None
        self._patches = [
            patch.object(rs, "PLAYWRIGHT_OK", True),
            patch.object(rs, "async_playwright", lambda: _FakeManager(), create=True),
            patch.object(rs, "_playwright_disabled", lambda **_: False),
        ]
        for p in self._patches:
            p.start()

    async def asyncTearDown(self):
        if rs._pw_idle_task:
            rs._pw_idle_task.cancel()
        async with rs._browser_lock():
            await rs._close_shared_browser()
        for p in self._patches:
            p.stop()

    async def test_concurrent_renders_survive_recycle_threshold(self):
        with patch.object(rs, "_PW_BROWSER_MAX_USES", 3):
            outs = await asyncio.gather(*[rs._html_pdf_playwright("<p>x</p>") for _ in range(12)])
        self.assertTrue(all(o == b"%PDF-fake" for o in outs))
        self.assertFalse(any(b.closed_with_open_pages for b in _FakeManager.launched))
        self.assertEqual(rs._pw_active_renders, 0)

    async def test_recycles_when_idle_between_renders(self):
        with patch.object(rs, "_PW_BROWSER_MAX_USES", 2):
            for _ in range(5):
                self.assertEqual(await rs._html_pdf_playwright("<p>x</p>"), b"%PDF-fake")
        self.assertGreaterEqual(len(_FakeManager.launched), 2)

    async def test_idle_browser_is_closed(self):
        with patch.object(rs, "_PW_IDLE_CLOSE_SEC", 0.05):
            self.assertEqual(await rs._html_pdf_playwright("<p>x</p>"), b"%PDF-fake")
            await asyncio.wait_for(rs._pw_idle_task, timeout=2)
        self.assertIsNone(rs._pw_browser)
        self.assertTrue(_FakeManager.launched[0].closed)
        # Next render relaunches transparently.
        self.assertEqual(await rs._html_pdf_playwright("<p>x</p>"), b"%PDF-fake")
        self.assertEqual(len(_FakeManager.launched), 2)


if __name__ == "__main__":
    unittest.main()
