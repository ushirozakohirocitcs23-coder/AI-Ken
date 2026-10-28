"""AI-KEN Retrieval-Augmented Generation pipeline.

 1 input → 2 text processing → 3 language detection → 4 emotion analysis (LLM, lexicon hints)
 → 5/6 embedding-based retrieval (poetry rules, techniques, dictionary) → 7 context augmentation
 → 8 generation → 9 structural validation → 10 revision (bounded) → 11 response payload.
Feedback (12) is handled by the poems router.
"""
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import DictionaryEntry, PoetryForm
from . import llm, vectorstore
from .audit import rag_log
from .dictionary import entry_dict, fil_lexicon, find_local, lookup
from .embeddings import fold
from .language import EMOTION_LABELS, EMOTIONS, LANG_NAMES, detect_language, lexicon_emotions, normalize_emotion
from .settings_store import get_setting
from .validation.phonetics import line_words
from .validation.validator import split_poem, validate

SUPPORT_NOTE = ("If you are going through something heavy, you don't have to carry it alone. Please reach out to "
                "someone you trust. In the Philippines you can call the NCMH Crisis Hotline at 1553 (24/7).")

SYSTEM_PERSONA = """You are AI-KEN, an empathetic poetry companion. You turn people's personal stories into short, \
original, meaningful poems in Filipino, English, or Taglish.
- Honor the user's feelings; never judge, dismiss, diagnose, or lecture.
- Emotion detection is an interpretation of the text, not a judgment of the person.
- Write ORIGINAL poems. Never copy published poems or song lyrics.
- Use natural Filipino (not word-for-word translation from English) when writing Filipino or Taglish.
- Use concrete imagery, metaphor and symbolism drawn from the user's own details.
- Obey structural constraints exactly (line count, syllables, rhyme, acrostic letters)."""

LEVEL_GUIDE = {"simple": "simple, everyday words a young reader understands",
               "intermediate": "clear but expressive vocabulary with a few rich words",
               "advanced": "rich, literary vocabulary and deeper figurative language"}


class PipelineError(RuntimeError):
    pass


@dataclass
class PoemRequest:
    story: str
    language: str = "auto"            # auto | fil | en | taglish
    poem_type: str = "auto"           # form key or auto
    lines: int | None = None
    syllable_pattern: str | None = None
    rhyme_scheme: str | None = None   # e.g. ABAB, none
    vocabulary_level: str = "intermediate"
    emotional_tone: list[str] = field(default_factory=list)
    show_vocabulary: bool = True
    acrostic_word: str | None = None
    traditional_meter: bool = True
    variation_of: str | None = None   # previous title, for regeneration

    def as_settings(self) -> dict:
        return {k: getattr(self, k) for k in ("language", "poem_type", "lines", "syllable_pattern", "rhyme_scheme",
                                               "vocabulary_level", "emotional_tone", "show_vocabulary",
                                               "acrostic_word", "traditional_meter")}


def clean_story(text: str, max_chars: int) -> str:
    text = text.replace("\r\n", "\n").replace("\x00", "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if not text:
        raise PipelineError("Please share a story or feeling to turn into a poem.")
    if len(text) > max_chars:
        raise PipelineError(f"Your story is too long ({len(text)} characters). Please keep it under {max_chars}.")
    return text


def _parse_pattern(p: str | None) -> list[int] | None:
    if not p:
        return None
    nums = [int(x) for x in re.findall(r"\d+", p)]
    return nums if nums and all(1 <= n <= 30 for n in nums) else None


def effective_rules(form: PoetryForm, req: PoemRequest, language: str) -> tuple[dict, list[str]]:
    """Merge form rules with user settings, keeping locked traditional fields. Returns (rules, notes)."""
    rules = {k: v for k, v in (form.rules or {}).items() if k not in {"locked", "controls"}}
    locked = set((form.rules or {}).get("locked", []))
    notes: list[str] = []

    if form.key == "acrostic":
        word = re.sub(r"[^A-Za-zÑñ]", "", req.acrostic_word or "") or "HOPE"
        word = word.upper()[:20]
        rules["acrostic"] = word
        rules["lines"] = len(word)
    if req.lines:
        if rules.get("lines"):  # fixed-length form (haiku, tanaga, sonnet, acrostic...)
            if req.lines != rules["lines"]:
                notes.append(f"{form.name} requires {rules['lines']} lines; your line setting was not applied.")
        elif rules.get("lines_multiple_of") and req.lines % rules["lines_multiple_of"]:
            notes.append(f"{form.name} uses {rules['lines_multiple_of']}-line stanzas; line count rounded.")
            m = rules["lines_multiple_of"]
            rules["lines"] = max(m, round(req.lines / m) * m)
        else:
            rules["lines"] = int(req.lines)
            rules.pop("lines_min", None)
            rules.pop("lines_max", None)
    pattern = _parse_pattern(req.syllable_pattern)
    if pattern:
        if {"syllables", "syllables_per_line"} & locked and form.key != "haiku":
            notes.append(f"{form.name} keeps its traditional syllable pattern.")
        elif form.key == "haiku" and pattern not in ([5, 7, 5], [3, 5, 3]):
            notes.append("Haiku keeps a 3-line short-long-short pattern (5-7-5 or 3-5-3).")
        else:
            rules.pop("syllables_per_line", None)
            rules["syllables"] = pattern
            rules.pop("syllable_mode", None)
    scheme = (req.rhyme_scheme or "").strip().upper()
    if scheme:
        options = [o.upper() for o in (form.rules or {}).get("controls", {}).get("rhyme_options", [])]
        if "rhyme" in locked:
            if scheme not in {rules.get("rhyme", "").replace(" ", ""), ""}:
                notes.append(f"{form.name} keeps its traditional rhyme scheme ({rules.get('rhyme')}).")
        elif options and scheme not in options and form.key != "custom":
            notes.append(f"Rhyme scheme {scheme} isn't used for {form.name}; kept {rules.get('rhyme') or 'no rhyme'}.")
        elif scheme in {"NONE", "NO RHYME"}:
            rules.pop("rhyme", None)
            rules.pop("rhyme_alternatives", None)
        else:
            rules["rhyme"] = scheme
            rules.pop("rhyme_alternatives", None)
            if form.key in {"ballad"}:
                rules["rhyme_repeat"] = True
            elif rules.get("lines") and len(scheme) < rules["lines"] and form.key not in {"tanaga"}:
                rules["rhyme_repeat"] = True
    # meter only meaningful for English sonnets/limericks
    if form.key.startswith("sonnet") and (not req.traditional_meter or language != "en"):
        rules.pop("syllables_per_line", None)
        rules.pop("syllable_mode", None)
        rules.pop("syllable_tolerance", None)
    if form.key == "limerick" and language != "en":
        for k in ("syllables", "syllable_mode", "syllable_tolerance", "syllable_label"):
            rules.pop(k, None)
    return rules, notes


def describe_constraints(rules: dict, form: PoetryForm, language: str) -> str:
    out = [f"Form: {form.name}"]
    if rules.get("lines"):
        out.append(f"Exactly {rules['lines']} lines (not counting blank stanza-separator lines).")
    elif rules.get("lines_min"):
        out.append(f"Between {rules['lines_min']} and {rules.get('lines_max', 40)} lines.")
    if rules.get("lines_multiple_of"):
        out.append(f"Use complete {rules['lines_multiple_of']}-line stanzas separated by blank lines.")
    if rules.get("syllables"):
        mode = " (approximately)" if rules.get("syllable_mode") == "approximate" else " EXACTLY"
        out.append(f"Syllables per line{mode}: {'-'.join(map(str, rules['syllables']))}"
                   + (" (pattern repeats)" if rules.get("lines", 0) > len(rules["syllables"]) else "") + ".")
    if rules.get("syllables_per_line"):
        mode = "about" if rules.get("syllable_mode") == "approximate" else "EXACTLY"
        out.append(f"Each line has {mode} {rules['syllables_per_line']} syllables.")
    if rules.get("rhyme"):
        alt = rules.get("rhyme_alternatives")
        per = " in every stanza (rhyme sounds may change between stanzas)" if rules.get("rhyme_per_stanza") else ""
        rep = " (pattern repeats)" if rules.get("rhyme_repeat") and not per else ""
        out.append(f"End-rhyme scheme: {rules['rhyme']}{per}{rep}" + (f" (or {', '.join(alt)})" if alt else "") + ".")
    else:
        out.append("No required rhyme.")
    if rules.get("acrostic"):
        out.append(f"Acrostic: line i must START with letter i of '{rules['acrostic']}' "
                   f"({', '.join(rules['acrostic'])}).")
    if rules.get("words_per_line"):
        out.append(f"Words per line: {'-'.join(map(str, rules['words_per_line']))}.")
    if language in {"fil", "taglish"} and (rules.get("syllables") or rules.get("syllables_per_line")):
        out.append("Filipino syllable counting: each vowel letter = 1 syllable; 'mga' = 2; 'ng' = 1; "
                   "use apostrophe contractions (puso'y, 'di, ako'y) to adjust counts.")
    return "\n".join(f"- {o}" for o in out)


LANG_INSTRUCTIONS = {
    "fil": "Write the poem entirely in natural, fluent Filipino (Tagalog-based). Avoid English words.",
    "en": "Write the poem entirely in English.",
    "taglish": "Write in natural Taglish: Filipino grammar backbone with English words/phrases where Filipinos "
               "naturally code-switch. Keep culture-specific feelings (kilig, tampo, hiya, sayang) in Filipino.",
}


# ---------------- steps ----------------
def analyze(db: Session, story: str, req: PoemRequest, input_lang: str, forms: list[PoetryForm]) -> dict:
    t0 = time.monotonic()
    hints = lexicon_emotions(story)
    form_keys = [f.key for f in forms if f.key != "custom"]
    prompt = f"""TASK: ANALYZE
Read the user's story and interpret its emotions. Story language detected: {LANG_NAMES.get(input_lang)}.
Allowed emotion categories: {", ".join(EMOTIONS)}.
Lexicon hints (may be incomplete): {json.dumps([h['emotion'] for h in hints])}
User-selected emotional tone (optional): {json.dumps(req.emotional_tone)}
Available poem forms: {", ".join(form_keys)}

STORY:
\"\"\"{story}\"\"\"

Return JSON:
{{"emotions":[{{"emotion":"<category>","label":"<short human label, e.g. exhaustion>","intensity":0.0-1.0,"evidence":"<few words from story>"}}],
 "themes":["<2-4 short themes>"],"tone":"<overall tone in a few words>","summary":"<one empathetic sentence reflecting the story back>",
 "recommended_form":"<one key from the available forms that suits this story>","recommended_reason":"<short reason>",
 "wellbeing_concern": <true only if the story mentions self-harm, suicide, abuse or immediate danger>}}"""
    try:
        data = llm.complete_json(SYSTEM_PERSONA, prompt, max_tokens=700, temperature=0.2)
        emotions = []
        for e in data.get("emotions", [])[:6]:
            cat = normalize_emotion(str(e.get("emotion", ""))) or normalize_emotion(str(e.get("label", "")))
            if not cat:
                continue
            emotions.append({"emotion": cat, "label": str(e.get("label") or EMOTION_LABELS[cat])[:40],
                             "intensity": max(0.0, min(1.0, float(e.get("intensity") or 0.5))),
                             "evidence": str(e.get("evidence") or "")[:120]})
        rec = data.get("recommended_form") if data.get("recommended_form") in form_keys else None
        result = {"emotions": emotions or hints, "themes": [str(t)[:40] for t in data.get("themes", [])][:4],
                  "tone": str(data.get("tone") or "")[:80], "summary": str(data.get("summary") or "")[:300],
                  "recommended_form": rec, "recommended_reason": str(data.get("recommended_reason") or "")[:200],
                  "wellbeing_concern": bool(data.get("wellbeing_concern")), "method": "llm"}
        rag_log(db, "analysis", True, int((time.monotonic() - t0) * 1000), len(emotions))
    except llm.LLMNotConfigured:
        raise
    except (llm.LLMError, ValueError, TypeError) as exc:
        rag_log(db, "analysis", False, int((time.monotonic() - t0) * 1000), detail=str(exc))
        result = {"emotions": hints, "themes": [], "tone": "", "summary": "", "recommended_form": None,
                  "recommended_reason": "", "wellbeing_concern": False, "method": "lexicon_fallback"}
    if req.emotional_tone:
        result["user_selected_tone"] = req.emotional_tone
    return result


def retrieve(db: Session, form: PoetryForm, analysis: dict, language: str, level: str) -> dict:
    t0 = time.monotonic()
    k = int(get_setting(db, "retrieval_top_k") or 6)
    emos = [e["emotion"] for e in analysis.get("emotions", [])] + list(analysis.get("user_selected_tone") or [])
    emo_words = " ".join(EMOTION_LABELS.get(e, e) for e in emos)
    themes = " ".join(analysis.get("themes", []))
    langs = {"fil": {"fil", "any"}, "en": {"en", "any"}, "taglish": {"fil", "en", "any"}}[language]
    try:
        rule_hits = vectorstore.search(db, f"{form.name} poetry form rules structure {form.description}", k=2,
                                       source_types={"document"}, categories={"poetry_rules"}, languages=None)
        ref_hits = vectorstore.search(db, f"{emo_words} {themes} imagery metaphor symbolism {LANG_NAMES[language]} poem",
                                      k=k, source_types={"document"}, languages=langs)
        dict_langs = {"fil": {"fil"}, "en": {"en"}, "taglish": {"fil", "en"}}[language]
        cats = {e for e in emos if e in EMOTIONS} or None
        dict_hits = vectorstore.search(db, f"{emo_words} {themes}", k=14, source_types={"dictionary"},
                                       languages=dict_langs, categories=cats, min_score=0.0)
        if len(dict_hits) < 6:
            dict_hits += vectorstore.search(db, f"{emo_words} {themes}", k=8, source_types={"dictionary"},
                                            languages=dict_langs, min_score=0.0)
    except Exception as exc:  # embedding service down etc.
        rag_log(db, "retrieval", False, int((time.monotonic() - t0) * 1000), detail=str(exc))
        return {"documents": [], "vocabulary": [], "error": "Knowledge-base retrieval is unavailable; generated "
                                                           "from form rules only."}
    seen, docs = set(), []
    for h in rule_hits + ref_hits:
        if h.chunk_id in seen:
            continue
        seen.add(h.chunk_id)
        docs.append({"chunk_id": h.chunk_id, "doc_id": h.source_id, "score": round(h.score, 3), "text": h.text})
    entries, seen_e = [], set()
    for h in dict_hits:
        if h.source_id in seen_e:
            continue
        e = db.get(DictionaryEntry, h.source_id)
        if not e:
            continue
        seen_e.add(e.id)
        entries.append((0 if e.level == level else 1, -h.score, e))
    entries.sort(key=lambda x: (x[0], x[1]))
    vocab = [entry_dict(e) | {"score": round(-s, 3)} for _, s, e in entries[:10]]
    top = max([d["score"] for d in docs] + [0])
    rag_log(db, "retrieval", True, int((time.monotonic() - t0) * 1000), len(docs) + len(vocab), top)
    return {"documents": docs, "vocabulary": vocab}


def _poem_json_spec() -> str:
    return ('Return JSON: {"title":"<short title in the poem language>","lines":["line 1","line 2", "", "line 3 (empty '
            'string = stanza break)"],"vocabulary":[{"word":"<notable word used in the poem>","meaning":"<brief meaning '
            'in the poem language>"}],"craft_note":"<one sentence on the technique used>"}')


def build_generation_prompt(story: str, req: PoemRequest, form: PoetryForm, rules: dict, language: str,
                            analysis: dict, retrieved: dict) -> str:
    emos = ", ".join(f"{e['label']} ({e['emotion']})" for e in analysis.get("emotions", [])) or "interpret from story"
    ctx = "\n\n".join(f"[{i + 1}] {d['text']}" for i, d in enumerate(retrieved.get("documents", [])[:8]))
    vocab = "; ".join(f"{v['word']} — {v['definition']}" for v in retrieved.get("vocabulary", [])[:10])
    tone = ", ".join(req.emotional_tone) if req.emotional_tone else "follow the story's emotions"
    variation = (f"\nThis is a NEW alternative version. Do not reuse the previous title \"{req.variation_of}\"; choose "
                 f"different images and wording." if req.variation_of else "")
    return f"""TASK: GENERATE
CONSTRAINTS_JSON: {json.dumps({"form": form.key, "language": language, **rules}, ensure_ascii=False)}

USER STORY:
\"\"\"{story}\"\"\"

INTERPRETED EMOTIONS: {emos}
THEMES: {", ".join(analysis.get("themes", [])) or "—"}
REQUESTED EMOTIONAL TONE: {tone}
LANGUAGE: {LANG_INSTRUCTIONS[language]}
VOCABULARY LEVEL: {req.vocabulary_level} — {LEVEL_GUIDE.get(req.vocabulary_level, "")}

FORM RULES (retrieved from the poetry knowledge base):
{form.guidance}

STRUCTURAL CONSTRAINTS (must be satisfied):
{describe_constraints(rules, form, language)}

RETRIEVED REFERENCES (use as craft guidance; do not copy text):
{ctx or "—"}

RETRIEVED DICTIONARY VOCABULARY (use 1-3 where natural, correctly):
{vocab or "—"}
{variation}
Write one original poem about the user's own story. Before answering, silently count syllables and check rhymes \
line by line. {_poem_json_spec()}"""


def _lines_from(data: dict) -> list[str]:
    raw = data.get("lines")
    if isinstance(raw, str):
        raw = raw.split("\n")
    if not isinstance(raw, list):
        raise llm.LLMError("The AI response did not include poem lines.")
    lines = [str(l).rstrip() for l in raw]
    while lines and not lines[-1].strip():
        lines.pop()
    while lines and not lines[0].strip():
        lines.pop(0)
    if not any(l.strip() for l in lines):
        raise llm.LLMError("The AI returned an empty poem.")
    return lines


def _revise(story: str, form: PoetryForm, rules: dict, language: str, current: dict, report: dict) -> dict:
    issues = "\n".join(f"- {i}" for i in report["issues"]) or "- (none)"
    counts = "\n".join(f"line {l['line']}: {l['syllables']} syllables" + (f" (target {l['target']})" if "target" in l else "")
                       + f" — {l['text']}" for l in report["lines"])
    prompt = f"""TASK: REVISE
CONSTRAINTS_JSON: {json.dumps({"form": form.key, "language": language, **rules}, ensure_ascii=False)}
The poem below failed structural validation. Fix ONLY what is needed while keeping its meaning, emotion and imagery
true to the user's story.

STORY (for meaning): \"\"\"{story[:1500]}\"\"\"
CONSTRAINTS:
{describe_constraints(rules, form, language)}
LANGUAGE: {LANG_INSTRUCTIONS[language]}

CURRENT POEM TITLE: {current.get('title')}
CURRENT LINES:
{chr(10).join(current['lines'])}

VALIDATOR FINDINGS:
{issues}
MEASURED SYLLABLES:
{counts}

Rewrite the poem so every constraint passes. {_poem_json_spec()}"""
    return llm.complete_json(SYSTEM_PERSONA, prompt, max_tokens=1200, temperature=0.4)


def generate_validated(db: Session, story: str, req: PoemRequest, form: PoetryForm, rules: dict, language: str,
                       analysis: dict, retrieved: dict) -> tuple[dict, dict, int]:
    lex = fil_lexicon(db)
    t0 = time.monotonic()
    data = llm.complete_json(SYSTEM_PERSONA, build_generation_prompt(story, req, form, rules, language, analysis,
                                                                     retrieved), max_tokens=1500, temperature=0.85)
    rag_log(db, "generation", True, int((time.monotonic() - t0) * 1000))
    data["lines"] = _lines_from(data)
    report = validate("\n".join(data["lines"]), rules, language, form.key, lex)
    best = (report["score"], data, report)
    attempts = 0
    max_rev = max(0, min(4, int(get_setting(db, "max_revision_attempts") or 0)))
    while report["overall"] == "fail" and attempts < max_rev:
        attempts += 1
        t1 = time.monotonic()
        try:
            revised = _revise(story, form, rules, language, data, report)
            revised["lines"] = _lines_from(revised)
        except llm.LLMError as exc:
            rag_log(db, "validation", False, int((time.monotonic() - t1) * 1000), detail=f"revision failed: {exc}")
            break
        revised.setdefault("vocabulary", data.get("vocabulary"))
        data = revised
        report = validate("\n".join(data["lines"]), rules, language, form.key, lex)
        rag_log(db, "validation", report["overall"] != "fail", int((time.monotonic() - t1) * 1000),
                detail=f"revision {attempts}: {report['overall']}")
        if report["score"] < best[0] or report["overall"] != "fail":
            best = (report["score"], data, report)
    _, data, report = best
    return data, report, attempts


def label_report(report: dict, form: PoetryForm, attempts: int, notes: list[str]) -> dict:
    report = dict(report)
    report["form_name"] = form.name
    report["tradition"] = form.tradition
    report["revision_attempts"] = attempts
    report["notes"] = notes
    if report["overall"] == "pass":
        report["status_label"] = f"Verified {form.name} structure"
    elif report["overall"] == "pass_estimate":
        report["status_label"] = f"{form.name} structure passed (some checks are estimates — review manually)"
    else:
        label = "traditional " if form.tradition == "traditional" else ""
        report["status_label"] = (f"Modern adaptation — did not fully satisfy the {label}{form.name} rules "
                                  f"after {attempts} revision(s)")
    return report


def build_vocabulary(db: Session, poem_lines: list[str], llm_vocab: list, retrieved_vocab: list, language: str) -> list[dict]:
    words_in_poem = {fold(w).strip("'’-") for l in poem_lines for w in line_words(l)}
    out: list[dict] = []
    seen: set[str] = set()
    lang_pref = None if language == "taglish" else language

    def add_entry(word: str, ai_meaning: str | None = None):
        key = fold(word).strip()
        if not key or key in seen or len(out) >= 6:
            return
        seen.add(key)
        local = find_local(db, key, lang_pref) or find_local(db, key)
        if local:
            out.append(entry_dict(local))
            return
        ext = lookup(db, key, "en") if language in {"en", "taglish"} else None
        if ext:
            out.append(ext)
            return
        if ai_meaning:
            out.append({"word": word, "language": language, "definition": ai_meaning, "synonyms": [], "antonyms": [],
                        "example": None, "source": "AI-generated explanation — not verified against a dictionary",
                        "verified": False, "provenance": "ai_generated"})

    for v in retrieved_vocab:  # dictionary words the poem actually used
        if fold(v["word"]) in words_in_poem or any(fold(v["word"]) in w for w in words_in_poem if len(v["word"]) > 4):
            add_entry(v["word"])
    for v in llm_vocab or []:
        if isinstance(v, dict) and v.get("word"):
            first = fold(str(v["word"])).split()
            if first and any(first[0] in w for w in words_in_poem):
                add_entry(str(v["word"]), str(v.get("meaning") or "")[:300] or None)
    return out


def run(db: Session, req: PoemRequest) -> dict:
    max_chars = int(get_setting(db, "max_story_chars") or 4000)
    story = clean_story(req.story, max_chars)
    ok, hint = llm.settings.llm_configured()
    if not ok:
        raise llm.LLMNotConfigured(hint)

    detected = detect_language(story)
    enabled_langs = get_setting(db, "enabled_languages") or ["fil", "en", "taglish"]
    language = req.language if req.language in {"fil", "en", "taglish"} else detected["language"]
    if language not in enabled_langs:
        if req.language != "auto":
            raise PipelineError(f"{LANG_NAMES.get(language, language)} output is currently disabled by the administrator.")
        language = enabled_langs[0]

    forms = db.scalars(select(PoetryForm).where(PoetryForm.enabled.is_(True))).all()
    if not forms:
        raise PipelineError("No poem forms are enabled. Ask an administrator to enable poetry forms.")
    analysis = analyze(db, story, req, detected["language"], forms)

    form_key = req.poem_type
    auto_chosen = False
    if form_key in {None, "", "auto"}:
        form_key = analysis.get("recommended_form") or ("tanaga" if language == "fil" else "quatrain")
        auto_chosen = True
    form = next((f for f in forms if f.key == form_key), None)
    if not form:
        if not auto_chosen:
            raise PipelineError("That poem type is not available right now.")
        form = next((f for f in forms if f.key == "free_verse"), forms[0])

    rules, notes = effective_rules(form, req, language)
    if auto_chosen:
        notes.insert(0, f"AI-KEN chose {form.name}: {analysis.get('recommended_reason') or 'it suits your story.'}")
    retrieved = retrieve(db, form, analysis, language, req.vocabulary_level)
    if retrieved.get("error"):
        notes.append(retrieved["error"])

    data, report, attempts = generate_validated(db, story, req, form, rules, language, analysis, retrieved)
    report = label_report(report, form, attempts, notes)
    vocab = (build_vocabulary(db, data["lines"], data.get("vocabulary") or [], retrieved.get("vocabulary", []), language)
             if req.show_vocabulary else [])
    db.commit()
    return {
        "title": str(data.get("title") or "Untitled")[:200],
        "content": "\n".join(data["lines"]).strip(),
        "craft_note": str(data.get("craft_note") or "")[:300],
        "language": language,
        "input_language": detected,
        "form": {"key": form.key, "name": form.name, "tradition": form.tradition},
        "rules": rules,
        "analysis": analysis,
        "validation": report,
        "vocabulary": vocab,
        "retrieval": {"documents": [{k: d[k] for k in ("doc_id", "chunk_id", "score")} | {"preview": d["text"][:160]}
                                    for d in retrieved.get("documents", [])],
                      "vocabulary_candidates": [v["word"] for v in retrieved.get("vocabulary", [])]},
        "support_note": SUPPORT_NOTE if analysis.get("wellbeing_concern") else None,
    }


def translate(db: Session, title: str, content: str, form: PoetryForm, rules: dict, target: str,
              source_language: str) -> dict:
    ok, hint = llm.settings.llm_configured()
    if not ok:
        raise llm.LLMNotConfigured(hint)
    lines, _ = split_poem(content)
    t0 = time.monotonic()
    strict = bool(rules.get("syllables") or rules.get("syllables_per_line") or rules.get("rhyme") or rules.get("acrostic"))
    prompt = f"""TASK: TRANSLATE
CONSTRAINTS_JSON: {json.dumps({"form": form.key, "language": target, **rules}, ensure_ascii=False)}
Translate this poem from {LANG_NAMES.get(source_language, source_language)} into {LANG_NAMES[target]}.
Preserve its emotional meaning, imagery and tone; use natural idiom rather than word-for-word translation.
{"Re-create the form so these constraints still hold in the new language:" + chr(10) + describe_constraints(rules, form, target) if strict else "Keep a similar number of lines."}
LANGUAGE: {LANG_INSTRUCTIONS[target]}

TITLE: {title}
POEM:
{content}

{_poem_json_spec()}"""
    data = llm.complete_json(SYSTEM_PERSONA, prompt, max_tokens=1500, temperature=0.5)
    data["lines"] = _lines_from(data)
    lex = fil_lexicon(db)
    tr_rules = dict(rules)
    report = validate("\n".join(data["lines"]), tr_rules, target, form.key, lex)
    attempts = 0
    if report["overall"] == "fail" and strict and int(get_setting(db, "max_revision_attempts") or 0) > 0:
        attempts = 1
        try:
            revised = _revise(content, form, tr_rules, target, data, report)
            revised["lines"] = _lines_from(revised)
            r2 = validate("\n".join(revised["lines"]), tr_rules, target, form.key, lex)
            if r2["score"] <= report["score"]:
                data, report = revised, r2
        except llm.LLMError:
            pass
    rag_log(db, "translation", True, int((time.monotonic() - t0) * 1000))
    report = label_report(report, form, attempts, [f"Translated from {LANG_NAMES.get(source_language, source_language)}."
                                                  " Structure was re-checked in the new language."])
    vocab = build_vocabulary(db, data["lines"], data.get("vocabulary") or [], [], target)
    db.commit()
    return {"title": str(data.get("title") or title)[:200], "content": "\n".join(data["lines"]).strip(),
            "validation": report, "vocabulary": vocab, "language": target}


def gloss(word: str, language: str, context: str | None = None) -> dict:
    """LLM explanation for a word missing from the dictionary — always labeled unverified."""
    prompt = f"""TASK: GLOSS
Explain the word "{word}" ({LANG_NAMES.get(language, language)}){' as used in: ' + context[:300] if context else ''}.
Return JSON: {{"definition":"<plain meaning>","synonyms":["..."],"antonyms":["..."],"example":"<example sentence>"}}"""
    data = llm.complete_json(SYSTEM_PERSONA, prompt, max_tokens=400, temperature=0.2)
    return {"word": word, "language": language, "definition": str(data.get("definition") or "")[:400],
            "synonyms": [str(s) for s in (data.get("synonyms") or [])][:6],
            "antonyms": [str(s) for s in (data.get("antonyms") or [])][:6], "example": data.get("example"),
            "source": "AI-generated explanation — not verified against a dictionary", "verified": False,
            "provenance": "ai_generated"}
