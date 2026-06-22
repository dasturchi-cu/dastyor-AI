"""Shared pytest configuration."""
from __future__ import annotations

import os

os.environ.setdefault("USE_REDIS", "0")
os.environ.setdefault("ALLOW_INSECURE_AUTH", "1")
