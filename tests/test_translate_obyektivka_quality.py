"""Obyektivka tarjima sifati — til aralashmasligi va garbage filtri."""
from __future__ import annotations

import asyncio

import pytest

from features.ai.gemini_client import is_ai_garbage
from features.bot.handlers.translate import (
    _collect_translatable_strings,
    _finalize_obyektivka_translation,
    _local_translate_phrase,
    translate_payload,
)
from features.obyektivka.objective_data import build_objective_data
from features.obyektivka.translate_phrases import (
    format_birth_year_place,
    relationship_label,
    translate_awards_phrase,
)


def test_person_names_not_collected_for_translation() -> None:
    payload = {
        "fullname": "Karimov Jasur Alisherovich",
        "relatives": [
            {
                "degree": "onasi",
                "fullname": "Karimova Erali",
                "birth_year_place": "1972-yilda",
                "work_place": "O'qituvchi",
            }
        ],
    }
    paths = {tuple(path) for path, _ in _collect_translatable_strings(payload)}
    assert ("fullname",) not in paths
    assert ("relatives", 0, "fullname") not in paths
    assert ("relatives", 0, "name") not in paths


def test_russian_ai_garbage_detected() -> None:
    text = "Меня готовы перевести. Какой текст из узбекского я должен перевести? none"
    assert is_ai_garbage(text)


def test_local_education_en() -> None:
    assert _local_translate_phrase("oliy", "uz_en") == "Higher"
    assert _local_translate_phrase("yuqori", "uz_en") == "Higher"


def test_local_education_ru() -> None:
    assert _local_translate_phrase("oliy", "uz_ru") == "Высшее"


def test_birth_year_place_formatting() -> None:
    assert format_birth_year_place("1972-yilda", "uz_en") == "In 1972"
    assert format_birth_year_place("1972-yilda", "uz_ru") == "В 1972 году"


def test_relationship_label_for_export() -> None:
    assert relationship_label("onasi", "en") == "Mother"
    assert relationship_label("onasi", "ru") == "Мать"


def test_finalize_scrubs_nationality_garbage() -> None:
    payload = {
        "fullname": "Test User",
        "nation": "Меня готовы перевести. Какой текст на узбекском я должен перевести?",
        "party": "yo'q",
        "education": "oliy",
        "current_job": "Dasturchi",
        "current_job_year": "2020-yildan buyon",
    }
    _finalize_obyektivka_translation(payload, "en")
    assert payload["nation"] == "none"
    assert payload["party"] == "none"
    assert payload["education"] == "Higher"
    assert payload["current_job_year"].startswith("Since 2020")


def test_translate_payload_keeps_relative_name(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_batch(texts, direction, **kwargs):
        return ["Early Karimov" if "Erali" in t else "Teacher" for t in texts]

    monkeypatch.setattr(
        "features.bot.handlers.translate.translate_strings_batch",
        fake_batch,
    )
    payload = {
        "fullname": "Karimov Jasur",
        "relatives": [
            {
                "degree": "onasi",
                "fullname": "Karimova Erali",
                "birth_year_place": "1972-yilda",
                "work_place": "O'qituvchi",
            }
        ],
        "education": "oliy",
        "nation": "O'zbek",
        "party": "yo'q",
        "current_job": "Dasturchi",
        "current_job_year": "2020",
    }
    out = asyncio.run(translate_payload(payload, "en"))
    assert out["relatives"][0]["fullname"] == "Karimova Erali"
    obj = build_objective_data(out)
    assert obj["relatives_table"][0]["relationship"] == "Mother"
    assert obj["relatives_table"][0]["full_name"] == "Karimova Erali"


def test_sanitize_rejects_russian_leak_in_english() -> None:
    from features.bot.handlers.translate import _sanitize_translated_value

    assert _sanitize_translated_value("O'qituvchi", "Учителя", "uz_en") == "Teacher"
    assert _sanitize_translated_value("Karimova Erali", "Ранний Карабои", "uz_en") == "Karimova Erali"


def test_awards_cyrillic_phrase() -> None:
    raw = '2005 й. "Шухрати" медал, 2010 й. "Меҳнат шуҳрати" ордени'
    out = translate_awards_phrase(raw, "uz_en")
    assert out is not None
    assert "2005" in out
    assert "medal" in out.lower() or "Shukhrati" in out
