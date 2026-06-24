"""Bot slash command definitions."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

from shared.bot_commands import BOT_COMMANDS, register_bot_commands


def test_bot_commands_include_required_slash_commands():
    names = {c.command for c in BOT_COMMANDS}
    assert names >= {"start", "cv", "obyektivka", "balance", "contact", "help"}
    assert all("@" not in c.command for c in BOT_COMMANDS)


def test_register_bot_commands_private_only():
    async def _run() -> None:
        bot = AsyncMock()
        await register_bot_commands(bot)
        bot.set_my_commands.assert_awaited_once()
        args, kwargs = bot.set_my_commands.await_args
        assert args[0][0].command == "start"
        assert kwargs["scope"].__class__.__name__ == "BotCommandScopeAllPrivateChats"
        assert bot.delete_my_commands.await_count == 2

    asyncio.run(_run())
