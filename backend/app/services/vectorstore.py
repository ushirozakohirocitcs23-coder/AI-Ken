"""Database-backed vector store.

Embeddings are stored as float32 blobs in the `kb_chunks` table (works on SQLite and
PostgreSQL). At query time the vectors for the active embedding model are loaded into an
in-memory NumPy matrix (cached and invalidated on every write) and ranked by cosine
similarity. This handles tens of thousands of chunks comfortably; for larger corpora swap
this module for pgvector/ChromaDB — the `add_chunks`/`search` interface stays the same.
"""
from __future__ import annotations

import re
import threading
from dataclasses import dataclass

import numpy as np
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..models import KnowledgeChunk
from .embeddings import embed_texts, model_id

_lock = threading.Lock()
_cache: dict = {"version": -1, "model": None, "matrix": None, "rows": []}
_version = 0


def _bump() -> None:
    global _version
    with _lock:
        _version += 1


@dataclass
class Hit:
    chunk_id: int
    source_type: str
    source_id: int
    language: str
    category: str | None
    text: str
    score: float


def chunk_text(text: str, max_chars: int = 900, overlap: int = 150) -> list[str]:
    """Split on headings/paragraphs, then pack into ~max_chars windows with overlap."""
    paras = [p.strip() for p in re.split(r"\n\s*\n|(?=\n#{1,6} )", text) if p.strip()]
    chunks: list[str] = []
    buf = ""
    for p in paras:
        if len(p) > max_chars:
            sentences = re.split(r"(?<=[.!?])\s+", p)
        else:
            sentences = [p]
        for s in sentences:
            if len(buf) + len(s) + 2 > max_chars and buf:
                chunks.append(buf.strip())
                buf = buf[-overlap:] if overlap else ""
            buf += ("\n\n" if buf else "") + s
    if buf.strip():
        chunks.append(buf.strip())
    return chunks


def add_chunks(db: Session, source_type: str, source_id: int, texts: list[str], language: str,
               category: str | None = None) -> int:
    vecs = embed_texts(texts)
    mid = model_id()
    for t, v in zip(texts, vecs):
        db.add(KnowledgeChunk(source_type=source_type, source_id=source_id, language=language, category=category,
                              text=t, embedding=v.astype(np.float32).tobytes(), embedding_model=mid, dim=int(v.shape[0])))
    _bump()
    return len(texts)


def remove_source(db: Session, source_type: str, source_id: int) -> None:
    db.execute(delete(KnowledgeChunk).where(KnowledgeChunk.source_type == source_type,
                                            KnowledgeChunk.source_id == source_id))
    _bump()


def _load(db: Session):
    mid = model_id()
    with _lock:
        if _cache["version"] == _version and _cache["model"] == mid:
            return _cache["matrix"], _cache["rows"]
        current = _version
    rows = db.execute(select(KnowledgeChunk.id, KnowledgeChunk.source_type, KnowledgeChunk.source_id,
                             KnowledgeChunk.language, KnowledgeChunk.category, KnowledgeChunk.text,
                             KnowledgeChunk.embedding).where(KnowledgeChunk.embedding_model == mid)).all()
    matrix = (np.vstack([np.frombuffer(r.embedding, dtype=np.float32) for r in rows])
              if rows else np.zeros((0, 1), dtype=np.float32))
    meta = [(r.id, r.source_type, r.source_id, r.language, r.category, r.text) for r in rows]
    with _lock:
        _cache.update(version=current, model=mid, matrix=matrix, rows=meta)
    return matrix, meta


def search(db: Session, query: str, k: int = 5, source_types: set[str] | None = None,
           languages: set[str] | None = None, categories: set[str] | None = None,
           min_score: float = 0.05) -> list[Hit]:
    matrix, rows = _load(db)
    if not rows:
        return []
    q = embed_texts([query])[0]
    if matrix.shape[1] != q.shape[0]:
        return []
    scores = matrix @ q
    order = np.argsort(-scores)
    hits: list[Hit] = []
    for idx in order:
        cid, st, sid, lang, cat, text = rows[idx]
        s = float(scores[idx])
        if s < min_score:
            break
        if source_types and st not in source_types:
            continue
        if languages and lang not in languages and lang != "any":
            continue
        if categories and cat not in categories:
            continue
        hits.append(Hit(cid, st, sid, lang, cat, text, s))
        if len(hits) >= k:
            break
    return hits


def stats(db: Session) -> dict:
    from sqlalchemy import func
    mid = model_id()
    total = db.scalar(select(func.count(KnowledgeChunk.id))) or 0
    current = db.scalar(select(func.count(KnowledgeChunk.id)).where(KnowledgeChunk.embedding_model == mid)) or 0
    return {"total_chunks": total, "chunks_current_model": current, "stale_chunks": total - current,
            "embedding_model": mid}
