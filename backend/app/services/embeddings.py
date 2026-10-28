"""Text embedding providers.

EMBEDDING_PROVIDER=local  (default) – an offline signed feature-hashing embedder (word unigrams,
    word bigrams and character trigrams, 768 dims). It needs no API key and works for Filipino and
    English, but it is LEXICAL: it matches shared words/sub-words, not deep meaning.
EMBEDDING_PROVIDER=openai – any OpenAI-compatible /embeddings endpoint (OpenAI
    text-embedding-3-small, Voyage AI via EMBEDDING_BASE_URL=https://api.voyageai.com/v1, Ollama
    nomic-embed-text via http://localhost:11434/v1, ...). Recommended for semantic retrieval.

Changing the provider/model changes `model_id()`; re-process the knowledge base afterwards
(Admin → Knowledge Base → "Reprocess all") so stored vectors match the query vectors.
"""
from __future__ import annotations

import hashlib
import math
import re
import unicodedata

import httpx
import numpy as np

from ..config import settings

LOCAL_DIM = 768
_WORD = re.compile(r"[a-zñ]+(?:-[a-zñ]+)*")


class EmbeddingError(RuntimeError):
    pass


def model_id() -> str:
    if settings.embedding_provider == "openai":
        return f"openai:{settings.embedding_model}"
    return f"local-hash-v1-{LOCAL_DIM}"


def fold(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in text if not unicodedata.combining(c) or c == "̃")


def _h(token: str) -> int:
    return int.from_bytes(hashlib.blake2b(token.encode(), digest_size=8).digest(), "little")


def _local_embed(text: str) -> np.ndarray:
    vec = np.zeros(LOCAL_DIM, dtype=np.float32)
    words = _WORD.findall(fold(text))
    feats: dict[str, float] = {}
    for w in words:
        feats["w:" + w] = feats.get("w:" + w, 0) + 1.0
        padded = f"#{w}#"
        for i in range(len(padded) - 2):
            g = "c:" + padded[i:i + 3]
            feats[g] = feats.get(g, 0) + 0.35
    for a, b in zip(words, words[1:]):
        feats[f"b:{a}_{b}"] = feats.get(f"b:{a}_{b}", 0) + 0.7
    for f, tf in feats.items():
        h = _h(f)
        weight = (1 + math.log(tf)) if tf >= 1 else tf
        vec[h % LOCAL_DIM] += (1.0 if (h >> 63) & 1 else -1.0) * weight
    norm = float(np.linalg.norm(vec))
    return vec / norm if norm else vec


def _remote_embed(texts: list[str]) -> list[np.ndarray]:
    if not settings.embedding_api_key and "localhost" not in settings.embedding_base_url:
        raise EmbeddingError("EMBEDDING_PROVIDER=openai requires EMBEDDING_API_KEY.")
    out: list[np.ndarray] = []
    headers = {"content-type": "application/json"}
    if settings.embedding_api_key:
        headers["authorization"] = f"Bearer {settings.embedding_api_key}"
    for i in range(0, len(texts), 64):
        batch = texts[i:i + 64]
        try:
            r = httpx.post(settings.embedding_base_url.rstrip("/") + "/embeddings", headers=headers,
                           json={"model": settings.embedding_model, "input": batch}, timeout=60)
        except httpx.HTTPError as exc:
            raise EmbeddingError(f"Embedding service unreachable: {exc}") from exc
        if r.status_code != 200:
            raise EmbeddingError(f"Embedding API status {r.status_code}: {r.text[:200]}")
        data = sorted(r.json()["data"], key=lambda d: d.get("index", 0))
        for d in data:
            v = np.asarray(d["embedding"], dtype=np.float32)
            n = float(np.linalg.norm(v))
            out.append(v / n if n else v)
    return out


def embed_texts(texts: list[str]) -> list[np.ndarray]:
    if not texts:
        return []
    if settings.embedding_provider == "openai":
        return _remote_embed(texts)
    return [_local_embed(t) for t in texts]


def embedding_status() -> dict:
    remote = settings.embedding_provider == "openai"
    return {
        "provider": settings.embedding_provider,
        "model": model_id(),
        "configured": (not remote) or bool(settings.embedding_api_key) or "localhost" in settings.embedding_base_url,
        "note": ("Offline lexical hashing embeddings. Configure EMBEDDING_PROVIDER=openai for semantic retrieval."
                 if not remote else "Remote embedding model."),
    }
