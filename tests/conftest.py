"""Shared pytest configuration."""
from __future__ import annotations

import os

# Force non-production test environment (must be set before config.settings import).
os.environ["_HUJJATCHI_TEST"] = "1"
os.environ["USE_REDIS"] = "0"
os.environ["SKIP_WEBHOOK"] = "1"
os.environ["ALLOW_INSECURE_AUTH"] = "1"
os.environ["AUTO_APPROVE_PAYMENTS"] = "0"
