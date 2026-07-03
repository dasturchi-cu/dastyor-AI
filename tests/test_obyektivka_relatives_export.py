"""Qarindoshlar jadvali — tarjimadan keyin slotga tushishi."""
from __future__ import annotations

from features.bot.handlers.translate import _collect_translatable_strings
from features.obyektivka.objective_data import build_placeholder_context


def test_relationship_degree_not_translated() -> None:
    payload = {
        "relatives": [
            {
                "degree": "onasi",
                "fullname": "Karimova Ra'no",
                "birth_year_place": "1972",
                "work_place": "Teacher",
            }
        ]
    }
    paths = [path for path, _ in _collect_translatable_strings(payload)]
    assert ["relatives", 0, "degree"] not in paths
    assert ["relatives", 0, "type"] not in paths


def test_russian_translated_degree_still_maps() -> None:
    raw = {
        "lang": "ru",
        "fullname": "Test User",
        "relatives": [
            {
                "degree": "Мать",
                "fullname": "Karimova Ra'no",
                "birth_year_place": "1972-yilda",
                "work_place": "O'qituvchi",
                "address": "Toshkent",
            }
        ],
    }
    ctx = build_placeholder_context(raw)
    assert ctx.get("ona") == "Karimova Ra'no"
    assert ctx.get("_has_relatives") == "1"


def test_uzbek_degree_maps_for_english_export() -> None:
    raw = {
        "lang": "en",
        "fullname": "Test User",
        "relatives": [
            {
                "type": "onasi",
                "name": "Karimova Ra'no",
                "birth": "1972",
                "job": "Teacher",
                "addr": "Tashkent",
            }
        ],
    }
    ctx = build_placeholder_context(raw)
    assert ctx.get("ona") == "Karimova Ra'no"
    assert ctx.get("ona_ish") == "Teacher"
