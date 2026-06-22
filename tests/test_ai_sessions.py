import pytest

from database.repositories import ai_sessions as sessions_repo


def test_normalize_session_type_accepts_voice_labels():
    assert sessions_repo.normalize_session_type("cv_voice") == "cv_voice"
    assert sessions_repo.normalize_session_type("oby_voice") == "oby_voice"


def test_normalize_session_type_maps_legacy_labels():
    assert sessions_repo.normalize_session_type("cv_text") == "cv_voice"
    assert sessions_repo.normalize_session_type("oby_text") == "oby_voice"


def test_normalize_session_type_rejects_unknown():
    with pytest.raises(ValueError):
        sessions_repo.normalize_session_type("invalid")
