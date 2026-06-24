"""Map WebApp payload → master template placeholder context (via buildObjectiveData)."""

from __future__ import annotations

from typing import Any

from features.obyektivka.objective_data import (
    buildObjectiveData,
    build_objective_data,
    build_placeholder_context,
    objective_to_template_context,
)

__all__ = [
    "buildObjectiveData",
    "build_objective_data",
    "build_placeholder_context",
    "objective_to_template_context",
]
