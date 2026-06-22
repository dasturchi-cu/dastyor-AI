"""Regression: nested exception lookup must not recurse infinitely."""
from __future__ import annotations

from backend.exception_handlers import _find_nested_exception
from fastapi import HTTPException


def test_find_nested_exception_stops_on_cycle():
    a = RuntimeError("outer")
    b = ValueError("inner")
    a.__cause__ = b
    b.__cause__ = a
    found = _find_nested_exception(a, HTTPException)
    assert found is None


def test_find_nested_exception_finds_http_in_cause_chain():
    inner = HTTPException(status_code=404, detail="missing")
    outer = RuntimeError("wrap")
    outer.__cause__ = inner
    found = _find_nested_exception(outer, HTTPException)
    assert found is inner
