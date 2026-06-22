"""Unified progress stages for bot + WebApp (perceived instant feedback)."""
from __future__ import annotations

STAGES: tuple[tuple[str, str], ...] = (
    ("audio_received", "Audio qabul qilindi"),
    ("ai_analyzing", "AI tahlil qilmoqda"),
    ("data_extracted", "Ma'lumotlar ajratildi"),
    ("doc_generating", "Hujjat yaratilmoqda"),
    ("ready", "Tayyor"),
)

STAGES_TEXT: tuple[tuple[str, str], ...] = (
    ("text_received", "Matn qabul qilindi"),
    ("ai_analyzing", "AI tahlil qilmoqda"),
    ("data_extracted", "Ma'lumotlar ajratildi"),
    ("doc_generating", "Hujjat yaratilmoqda"),
    ("ready", "Tayyor"),
)

STEP_AUDIO = 1
STEP_AI = 2
STEP_EXTRACTED = 3
STEP_DOC = 4
STEP_READY = 5


def stage_label(step: int) -> str:
    idx = max(0, min(len(STAGES) - 1, step - 1))
    return STAGES[idx][1]


def telegram_message(
    current_step: int,
    *,
    highlight: str | None = None,
    input_mode: str = "audio",
) -> str:
    """Multi-line progress for Telegram status edits."""
    stages = STAGES_TEXT if input_mode == "text" else STAGES
    lines: list[str] = []
    for i, (_, label) in enumerate(stages, start=1):
        if i < current_step:
            mark = "✅"
        elif i == current_step:
            mark = "⏳"
        else:
            mark = "○"
        lines.append(f"{mark} {i}. {label}")
    body = "\n".join(lines)
    if highlight:
        return f"{body}\n\n{highlight}"
    return body


def web_steps_payload(current_step: int) -> dict:
    return {
        "step": current_step,
        "label": stage_label(current_step),
        "steps": [label for _, label in STAGES],
    }
