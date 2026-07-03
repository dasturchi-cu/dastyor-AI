"""Bot /translate handler helpers."""
from __future__ import annotations

import pytest

from features.bot.handlers.translate import (
    TranslationError,
    _direction_for,
    _parse_action,
    _template_lang_code,
)


def test_parse_action_cv_and_oby() -> None:
    assert _parse_action("tr_cv_en") == ("cv", "en")
    assert _parse_action("tr_oby_ru") == ("obyektivka", "ru")


def test_parse_action_invalid() -> None:
    with pytest.raises(TranslationError):
        _parse_action("tr_bad_en")
    with pytest.raises(TranslationError):
        _parse_action("tr_cv_uz")


def test_direction_mapping_uzbek_source_only() -> None:
    assert _direction_for("en") == "uz_en"
    assert _direction_for("ru") == "uz_ru"
    with pytest.raises(TranslationError):
        _direction_for("uz")


def test_template_lang_code_targets() -> None:
    assert _template_lang_code("en") == "en"
    assert _template_lang_code("ru") == "ru"
    with pytest.raises(TranslationError):
        _template_lang_code("uz")
