from __future__ import annotations

from sqlalchemy.orm import Session

from ..models import SystemSetting

DEFAULTS: dict = {
    "enabled_languages": ["fil", "en", "taglish"],
    "daily_generation_limit": 50,      # poems per user per day (0 = unlimited)
    "max_revision_attempts": 2,        # LLM revision rounds after a failed validation
    "registration_open": True,
    "max_story_chars": 4000,
    "retrieval_top_k": 6,
    "show_word_of_day": True,
}

DESCRIPTIONS = {
    "enabled_languages": "Output languages users may choose (fil, en, taglish).",
    "daily_generation_limit": "Maximum poems (including regenerations/translations) per user per day. 0 = unlimited.",
    "max_revision_attempts": "How many times AI-KEN may revise a poem that fails structural validation (0–4).",
    "registration_open": "Allow new public sign-ups.",
    "max_story_chars": "Maximum length of a submitted story.",
    "retrieval_top_k": "Number of knowledge-base chunks retrieved per generation.",
    "show_word_of_day": "Show Vocabulary of the Day in the user sidebar.",
}


def get_setting(db: Session, key: str):
    row = db.get(SystemSetting, key)
    return row.value if row is not None else DEFAULTS.get(key)


def all_settings(db: Session) -> dict:
    return {k: get_setting(db, k) for k in DEFAULTS}


def set_setting(db: Session, key: str, value) -> None:
    if key not in DEFAULTS:
        raise KeyError(key)
    row = db.get(SystemSetting, key)
    if row is None:
        db.add(SystemSetting(key=key, value=value))
    else:
        row.value = value
