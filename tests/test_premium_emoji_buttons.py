"""Tests for premium emoji button formatting and emoji stripping."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from shared import keyboards
from shared.premium_emoji import EMOJI_MAP, leading_emoji_id, strip_leading_emoji


def test_strip_leading_emoji():
    assert strip_leading_emoji("✍️ Obyektivka yaratish") == "Obyektivka yaratish"
    assert strip_leading_emoji("💳 Pul balansi") == "Pul balansi"
    assert strip_leading_emoji("📄 CV Resume") == "CV Resume"
    assert strip_leading_emoji("Oddiy Matn") == "Oddiy Matn"
    assert strip_leading_emoji("") == ""
    assert strip_leading_emoji(None) == ""


def test_kb_removes_leading_emoji_when_custom_icon_set():
    btn = keyboards._kb("✍️ Obyektivka yaratish")
    assert btn.text == "Obyektivka yaratish"
    assert btn.icon_custom_emoji_id == EMOJI_MAP["✍️"]


def test_ikb_removes_leading_emoji_when_custom_icon_set():
    ibtn = keyboards._ikb("📝 Muqova xati", callback_data="test")
    assert ibtn.text == "Muqova xati"
    assert ibtn.icon_custom_emoji_id == EMOJI_MAP["📝"]
    assert ibtn.callback_data == "test"


def test_is_btn_match():
    assert keyboards.is_btn_match("Obyektivka yaratish", keyboards.BTN_OBY)
    assert keyboards.is_btn_match("✍️ Obyektivka yaratish", keyboards.BTN_OBY)
    assert not keyboards.is_btn_match("Boshqa matn", keyboards.BTN_OBY)


def test_btn_filter():
    flt = keyboards.btn_filter(keyboards.BTN_OBY)

    msg1 = MagicMock(text="Obyektivka yaratish")
    msg2 = MagicMock(text="✍️ Obyektivka yaratish")
    msg3 = MagicMock(text="Boshqa matn")

    assert flt(msg1) is True
    assert flt(msg2) is True
    assert flt(msg3) is False


def test_cv_button_has_premium_icon():
    btn = keyboards._kb(keyboards.BTN_CV)
    assert btn.text == "CV Resume"
    assert btn.icon_custom_emoji_id == EMOJI_MAP["📄"]


@pytest.mark.asyncio
async def test_safe_react():
    from unittest.mock import AsyncMock

    from shared.premium_emoji import safe_react

    msg = MagicMock()
    msg.react = AsyncMock()
    await safe_react(msg, "⚡️")
    msg.react.assert_called_once()


def test_waving_hand_emoji_in_map():
    assert "👋" in EMOJI_MAP
    assert EMOJI_MAP["👋"] == "5436040291507247633"


def test_headphones_emoji_in_map():
    assert "🎧" in EMOJI_MAP
    assert EMOJI_MAP["🎧"] == "5382013970905309819"


def test_bullet_and_list_emojis_in_map():
    from shared.premium_emoji import premiumize

    for char in ("⚪", "⚪️", "⚫", "🔘", "🔹", "🔸", "⭐", "📋", "🔍"):
        assert char in EMOJI_MAP

    sample_progress_text = "✅ 1. audio_received\n⏳ 2. ai_analyzing\n○ 3. data_extracted\n○ 4. doc_generating"
    res = premiumize(sample_progress_text)
    assert '<tg-emoji emoji-id="' in res
    assert "○" in res
    assert "✅" in res
    assert "⏳" in res


