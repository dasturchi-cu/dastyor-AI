"""Live admin dashboard must stop refreshing on its own."""
from __future__ import annotations

import unittest
from unittest.mock import patch

from features.admin import dashboard


class _FakeBot:
    def __init__(self):
        self.edits: list[str] = []

    async def edit_message_text(self, text, **_):
        self.edits.append(text)


async def _no_sleep(_seconds):
    return None


class TestDashboardAutoStop(unittest.IsolatedAsyncioTestCase):
    async def test_loop_ends_after_live_window(self):
        bot = _FakeBot()
        session = dashboard.DashboardSession(admin_id=42, chat_id=1, message_id=2)
        dashboard._sessions[42] = session
        try:
            with patch.object(dashboard, "_LIVE_WINDOW_SEC", 0), patch.object(
                dashboard.asyncio, "sleep", _no_sleep
            ), patch.object(dashboard.stats_repo, "dashboard_snapshot", lambda: {}), patch.object(
                dashboard, "build_dashboard_text", lambda snapshot: "stats"
            ):
                await dashboard._refresh_loop(bot, session)
        finally:
            dashboard._sessions.pop(42, None)

        self.assertEqual(len(bot.edits), 1)
        self.assertIn("to'xtadi", bot.edits[0])
        self.assertNotIn(42, dashboard._sessions)


if __name__ == "__main__":
    unittest.main()
