"""Tests for domain-specific CV templates and Channel Auto-Poster."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from features.marketing.channel_autopost import SHOWCASE_TEMPLATES, send_channel_autopost


def test_cv_template_contains_domain_css_classes():
    tmpl_path = Path("templates/cv_template.html")
    assert tmpl_path.exists()
    content = tmpl_path.read_text(encoding="utf-8")
    assert ".tpl-it" in content
    assert ".tpl-finance" in content
    assert ".tpl-medical" in content
    assert ".tpl-marketing" in content


def test_webapp_cv_contains_domain_template_cards():
    cv_path = Path("webapp/cv.html")
    assert cv_path.exists()
    content = cv_path.read_text(encoding="utf-8")
    assert 'id="tpl-it"' in content
    assert 'id="tpl-finance"' in content
    assert 'id="tpl-medical"' in content
    assert 'id="tpl-marketing"' in content


@pytest.mark.asyncio
async def test_send_channel_autopost():
    bot = MagicMock()
    bot.send_message = AsyncMock()

    with patch("features.marketing.channel_autopost.Settings") as mock_settings_cls:
        settings_inst = MagicMock()
        settings_inst.marketing_channel_id = -100123456789
        settings_inst.bot_username = "DastyorAiBot"
        mock_settings_cls.return_value = settings_inst

        res = await send_channel_autopost(bot)
        assert res is True
        bot.send_message.assert_called_once()
        args, kwargs = bot.send_message.call_args
        assert kwargs["chat_id"] == -100123456789
        assert "Bot:" in kwargs["text"]
