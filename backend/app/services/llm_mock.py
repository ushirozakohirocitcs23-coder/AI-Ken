"""Deterministic offline LLM used ONLY by the automated test suite (APP_ENV=test,
LLM_PROVIDER=mock). It lets the tests exercise the full RAG → validation → revision flow
without network access. It is never selectable in development or production."""
from __future__ import annotations

import json
import re

from ..config import settings

HAIKU_EN = ["Behind my bright smile", "a tired heart keeps giving", "hoping to be seen"]
TANAGA_BAD = ["Masaya ako sa piling", "Ng pamilyang nagmamahal", "Ngunit may pangarap pa ring", "Hindi pa naaabot"]
TANAGA_OK = ["Sa piling ng pamilya", "Puso ko'y may ligaya", "Pangarap ay may luha", "Ngunit may pag-asa pa"]
QUATRAIN_AABB = ["I wear a smile beneath the light,", "While hiding tears beyond their sight.",
                 "I give my best, yet feel unseen,", "A tired heart behind a cheerful scene."]
QUATRAIN_ABAB = ["I wear a smile beneath the light,", "I give my best, yet feel unseen,",
                 "While hiding tears beyond their sight,", "A tired heart behind a cheerful scene."]
FREE_EN = ["Every morning I fold my tiredness", "into a small, bright smile", "and carry it like a lantern",
           "through rooms that never ask", "how heavy the light has become."]
FREE_FIL = ["Tuwing umaga, tinitiklop ko ang pagod", "sa isang maliit na ngiti,", "dala-dala tulad ng ilaw",
            "sa mga silid na hindi nagtatanong", "kung gaano na kabigat ang liwanag."]


def _constraints(prompt: str) -> dict:
    m = re.search(r"CONSTRAINTS_JSON: (\{.*\})", prompt)
    return json.loads(m.group(1)) if m else {}


def _poem(c: dict, revise: bool) -> list[str]:
    form, lang = c.get("form"), c.get("language")
    if c.get("acrostic"):
        return [f"{ch} is the light I carry still" for ch in c["acrostic"]]
    if form == "haiku":
        return HAIKU_EN
    if form in {"tanaga"}:
        return TANAGA_OK if revise else TANAGA_BAD
    if form in {"quatrain", "couplet"} and lang == "en":
        if form == "couplet":
            return QUATRAIN_AABB[:2]
        return QUATRAIN_ABAB if (c.get("rhyme") or "").replace(" ", "") == "ABAB" else QUATRAIN_AABB
    lines = FREE_FIL if lang == "fil" else FREE_EN
    n = c.get("lines") or len(lines)
    return [lines[i % len(lines)] for i in range(n)]


def mock_complete(system: str, prompt: str) -> str:
    if not settings.is_test:
        raise RuntimeError("Mock LLM is test-only.")
    task = re.search(r"TASK: (\w+)", prompt)
    task = task.group(1) if task else "GENERATE"
    if task == "ANALYZE":
        fil = any(w in prompt.lower() for w in ("pamilya", "masaya", "nalulungkot"))
        return json.dumps({
            "emotions": [{"emotion": "happiness" if fil else "sadness", "label": "joy" if fil else "exhaustion",
                          "intensity": 0.7, "evidence": "story"},
                         {"emotion": "hope", "label": "hope", "intensity": 0.5, "evidence": "someday"}],
            "themes": ["family" if fil else "being unseen", "dreams"], "tone": "tender",
            "summary": "You give so much, and you hope to be seen.",
            "recommended_form": "tanaga" if fil else "quatrain", "recommended_reason": "short and heartfelt",
            "wellbeing_concern": "hurt myself" in prompt.lower()})
    if task == "GLOSS":
        return json.dumps({"definition": "a mock explanation", "synonyms": ["x"], "antonyms": [], "example": "e.g."})
    c = _constraints(prompt)
    lines = _poem(c, revise=(task == "REVISE"))
    title = {"fil": "Sa Piling Mo", "en": "Behind My Smile"}.get(c.get("language"), "Behind My Smile")
    if task == "TRANSLATE" and c.get("language") == "fil":
        lines = TANAGA_OK if c.get("form") == "tanaga" else FREE_FIL[: max(2, min(5, c.get("lines") or 5))]
        title = "Sa Likod ng Ngiti"
    vocab = [{"word": "ligaya", "meaning": "matinding saya"}] if c.get("language") == "fil" else \
        [{"word": "unseen", "meaning": "not noticed"}, {"word": "lantern", "meaning": "a portable light"}]
    return "```json\n" + json.dumps({"title": title, "lines": lines, "vocabulary": vocab,
                                     "craft_note": "Uses contrast between light and tiredness."}) + "\n```"
