"""Tests for channel input normalization."""
from __future__ import annotations

from features.admin.channels import normalize_channel_input


def test_normalize_channel_input_urls():
    assert normalize_channel_input("https://t.me/freelanser_uzbek") == "@freelanser_uzbek"
    assert normalize_channel_input("http://t.me/freelanser_uzbek") == "@freelanser_uzbek"
    assert normalize_channel_input("t.me/freelanser_uzbek") == "@freelanser_uzbek"
    assert normalize_channel_input("t.me/freelanser_uzbek/123") == "@freelanser_uzbek"


def test_normalize_channel_input_usernames_and_ids():
    assert normalize_channel_input("@freelanser_uzbek") == "@freelanser_uzbek"
    assert normalize_channel_input("freelanser_uzbek") == "@freelanser_uzbek"
    assert normalize_channel_input("-1001234567890") == "-1001234567890"
    assert normalize_channel_input("1234567890") == "1234567890"


def test_normalize_private_channel_links():
    assert normalize_channel_input("https://t.me/c/1234567890/55") == "-1001234567890"
