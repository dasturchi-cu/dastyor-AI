"""Patronimik qo'shimcha tarjimasi."""
from __future__ import annotations

from shared.name_patronymic import translate_patronymic_suffixes


def test_ogli_to_english() -> None:
    assert translate_patronymic_suffixes("Alivaliyev Bekzod Anvar o'g'li", "uz_en") == (
        "Alivaliyev Bekzod Anvar son of"
    )


def test_ogli_to_russian() -> None:
    assert translate_patronymic_suffixes("Alivaliyev Bekzod Anvar o'g'li", "uz_ru") == (
        "Alivaliyev Bekzod Anvar угли"
    )


def test_qizi_to_english() -> None:
    assert translate_patronymic_suffixes("Karimova Malika Anvar qizi", "uz_en") == (
        "Karimova Malika Anvar daughter of"
    )
