"""Temp file helpers — avoid path leaks and always cleanup."""
from __future__ import annotations

import os
import tempfile
from contextlib import contextmanager
from typing import Generator


@contextmanager
def temp_image_path(suffix: str = ".bin") -> Generator[str, None, None]:
    fd, path = tempfile.mkstemp(prefix="dastyor_", suffix=suffix)
    os.close(fd)
    try:
        yield path
    finally:
        try:
            if os.path.exists(path):
                os.remove(path)
        except OSError:
            pass


def safe_remove(*paths: str | None) -> None:
    for p in paths:
        if not p:
            continue
        try:
            if os.path.exists(p):
                os.remove(p)
        except OSError:
            pass
