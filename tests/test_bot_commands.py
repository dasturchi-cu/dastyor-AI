"""Bot slash command definitions."""
from __future__ import annotations

from shared.bot_commands import BOT_COMMANDS


def test_bot_commands_include_required_slash_commands():
    names = {c.command for c in BOT_COMMANDS}
    assert names >= {"start", "cv", "obyektivka", "balance", "contact", "help"}
