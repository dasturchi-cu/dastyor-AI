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

STAGES_DOC: tuple[tuple[str, str], ...] = (
    ("request_received", "So'rov qabul qilindi"),
    ("data_checking", "Ma'lumotlar tekshirilmoqda"),
    ("doc_generating", "Hujjat tayyorlanmoqda"),
    ("file_sending", "Fayl yuborilmoqda"),
    ("ready", "Tayyor"),
)

STEP_AUDIO = 1
STEP_AI = 2
STEP_EXTRACTED = 3
STEP_DOC = 4
STEP_READY = 5


def stage_label(step: int, *, input_mode: str = "audio") -> str:
    if input_mode == "doc":
        stages = STAGES_DOC
    elif input_mode == "text":
        stages = STAGES_TEXT
    else:
        stages = STAGES
    idx = max(0, min(len(stages) - 1, step - 1))
    return stages[idx][1]


def telegram_message(
    current_step: int,
    *,
    highlight: str | None = None,
    input_mode: str = "audio",
) -> str:
    """Multi-line progress for Telegram status edits."""
    if input_mode == "doc":
        stages = STAGES_DOC
    elif input_mode == "text":
        stages = STAGES_TEXT
    else:
        stages = STAGES
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


def web_steps_payload(current_step: int, *, input_mode: str = "audio") -> dict:
    if input_mode == "doc":
        stages = STAGES_DOC
    elif input_mode == "text":
        stages = STAGES_TEXT
    else:
        stages = STAGES
    return {
        "step": current_step,
        "label": stage_label(current_step, input_mode=input_mode),
        "steps": [label for _, label in stages],
    }
