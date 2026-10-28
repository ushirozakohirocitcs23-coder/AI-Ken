"""Dictionary lookups with clear provenance.

Order: (1) curated database entry (verified or pending review), (2) for English, the Free
Dictionary API (dictionaryapi.dev, Wiktionary-derived) — cached into the database with its
source URL, (3) otherwise None. Callers that fall back to an LLM gloss must label it
"AI-generated, not verified".
"""
from __future__ import annotations

import hashlib
from datetime import date

import httpx
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import settings
from ..models import DictionaryEntry
from .embeddings import fold


def entry_dict(e: DictionaryEntry) -> dict:
    return {"id": e.id, "word": e.word, "language": e.language, "part_of_speech": e.part_of_speech,
            "definition": e.definition, "synonyms": e.synonyms or [], "antonyms": e.antonyms or [],
            "example": e.example, "emotion_category": e.emotion_category, "literary_usage": e.literary_usage,
            "level": e.level, "source": e.source, "source_url": e.source_url, "verified": e.verified,
            "provenance": "verified" if e.verified else "curated_unreviewed"}


def find_local(db: Session, word: str, language: str | None = None) -> DictionaryEntry | None:
    w = fold(word).strip()
    q = select(DictionaryEntry).where(func.lower(DictionaryEntry.word) == w)
    if language in {"fil", "en"}:
        q = q.where(DictionaryEntry.language == language)
    return db.scalar(q.order_by(DictionaryEntry.verified.desc()))


def fetch_english(db: Session, word: str) -> DictionaryEntry | None:
    if not settings.enable_external_dictionary:
        return None
    w = fold(word).strip()
    if not w.isalpha():
        return None
    try:
        r = httpx.get(settings.english_dictionary_api + w, timeout=6)
    except httpx.HTTPError:
        return None
    if r.status_code != 200:
        return None
    try:
        data = r.json()[0]
        meaning = data["meanings"][0]
        definition = meaning["definitions"][0]
    except (KeyError, IndexError, ValueError, TypeError):
        return None
    syn = list(dict.fromkeys((definition.get("synonyms") or []) + (meaning.get("synonyms") or [])))[:8]
    ant = list(dict.fromkeys((definition.get("antonyms") or []) + (meaning.get("antonyms") or [])))[:8]
    src_url = (data.get("sourceUrls") or [None])[0]
    e = DictionaryEntry(word=w, language="en", part_of_speech=meaning.get("partOfSpeech"),
                        definition=definition.get("definition", ""), synonyms=syn, antonyms=ant,
                        example=definition.get("example"), source="Free Dictionary API (dictionaryapi.dev, Wiktionary, CC BY-SA)",
                        source_url=src_url, verified=True, level="intermediate")
    db.add(e)
    db.commit()
    try:
        from .knowledge import index_entry
        index_entry(db, e)
        db.commit()
    except Exception:  # indexing failure must not break a lookup
        db.rollback()
    return e


def lookup(db: Session, word: str, language: str | None = None) -> dict | None:
    e = find_local(db, word, language)
    if not e and language in {None, "en", "taglish"}:
        e = fetch_english(db, word)
    return entry_dict(e) if e else None


def word_of_the_day(db: Session, language: str | None = None, day: date | None = None) -> dict | None:
    q = select(DictionaryEntry.id).order_by(DictionaryEntry.id)
    if language in {"fil", "en"}:
        q = q.where(DictionaryEntry.language == language)
    ids = db.scalars(q).all()
    if not ids:
        return None
    d = (day or date.today()).isoformat()
    idx = int(hashlib.sha256(d.encode()).hexdigest(), 16) % len(ids)
    return entry_dict(db.get(DictionaryEntry, ids[idx]))


def fil_lexicon(db: Session) -> frozenset[str]:
    words = db.scalars(select(DictionaryEntry.word).where(DictionaryEntry.language == "fil")).all()
    out = set()
    for w in words:
        out.add(fold(w))
        out.update(fold(p) for p in w.split("-"))
    return frozenset(out)
