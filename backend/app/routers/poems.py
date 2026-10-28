"""User module: conversations, poem generation, regeneration, translation, saving, feedback,
dictionary lookups and public metadata. Every query is scoped to the current user."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Conversation, Feedback, Message, PoetryForm, Poem, User, utcnow
from ..security import get_current_user, limiter
from ..services import llm, rag
from ..services.dictionary import lookup, word_of_the_day
from ..services.embeddings import embedding_status
from ..services.language import EMOTION_LABELS, detect_language
from ..services.settings_store import get_setting

router = APIRouter(prefix="/api", tags=["user"])
log = logging.getLogger("aiken.poems")


class PoemSettings(BaseModel):
    language: str = Field("auto", pattern="^(auto|fil|en|taglish)$")
    poem_type: str = Field("auto", max_length=40)
    lines: int | None = Field(None, ge=1, le=40)
    syllable_pattern: str | None = Field(None, max_length=60)
    rhyme_scheme: str | None = Field(None, max_length=30)
    vocabulary_level: str = Field("intermediate", pattern="^(simple|intermediate|advanced)$")
    emotional_tone: list[str] = Field(default_factory=list, max_length=4)
    show_vocabulary: bool = True
    acrostic_word: str | None = Field(None, max_length=20)
    traditional_meter: bool = True


class GenerateIn(BaseModel):
    story: str = Field(min_length=1, max_length=20000)
    conversation_id: int | None = None
    settings: PoemSettings = Field(default_factory=PoemSettings)


class RegenerateIn(BaseModel):
    settings: PoemSettings | None = None


class TranslateIn(BaseModel):
    target: str = Field(pattern="^(fil|en|taglish)$")


class PoemPatch(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=200)
    is_saved: bool | None = None


class ConvPatch(BaseModel):
    title: str = Field(min_length=1, max_length=200)


class FeedbackIn(BaseModel):
    rating: int = Field(ge=1, le=5)
    comments: str | None = Field(None, max_length=1000)


def _iso(dt):
    return dt.isoformat() if dt else None


def poem_out(p: Poem, feedback: Feedback | None = None) -> dict:
    return {"id": p.id, "conversation_id": p.conversation_id, "title": p.title, "content": p.content,
            "language": p.language, "poem_type": p.poem_type, "rhyme_scheme": p.rhyme_scheme,
            "detected_emotions": p.detected_emotions or [], "analysis": p.analysis or {}, "settings": p.settings or {},
            "validation": p.validation or {}, "vocabulary": p.vocabulary or [], "retrieval": p.retrieval or {},
            "kind": p.kind, "parent_poem_id": p.parent_poem_id, "is_saved": p.is_saved, "created_at": _iso(p.created_at),
            "feedback": {"rating": feedback.rating, "comments": feedback.comments} if feedback else None}


def message_out(m: Message, poems: dict[int, dict]) -> dict:
    return {"id": m.id, "sender": m.sender, "content": m.content, "meta": m.meta or {}, "created_at": _iso(m.created_at),
            "poem": poems.get(m.poem_id) if m.poem_id else None}


def _own_conv(db: Session, user: User, cid: int) -> Conversation:
    c = db.get(Conversation, cid)
    if not c or c.user_id != user.id:
        raise HTTPException(404, "Conversation not found.")
    return c


def _own_poem(db: Session, user: User, pid: int) -> Poem:
    p = db.get(Poem, pid)
    if not p or p.user_id != user.id:
        raise HTTPException(404, "Poem not found.")
    return p


def _check_quota(db: Session, user: User) -> None:
    limiter.check(f"gen:{user.id}", 12, 60)
    limit = int(get_setting(db, "daily_generation_limit") or 0)
    if limit:
        since = datetime.now(timezone.utc) - timedelta(days=1)
        used = db.scalar(select(func.count(Poem.id)).where(Poem.user_id == user.id, Poem.created_at >= since)) or 0
        if used >= limit:
            raise HTTPException(429, f"You've reached today's limit of {limit} poems. Please come back tomorrow.")


def _run_pipeline(db: Session, req: rag.PoemRequest) -> dict:
    try:
        return rag.run(db, req)
    except llm.LLMNotConfigured as exc:
        raise HTTPException(503, {"code": "llm_not_configured",
                                  "message": "AI poem generation is not set up yet. An administrator needs to configure "
                                             "the language-model API key.", "setup_hint": str(exc)})
    except rag.PipelineError as exc:
        raise HTTPException(400, str(exc))
    except llm.LLMError as exc:
        db.rollback()
        log.error("Generation failed: %s", exc)
        auth_problem = "status 401" in str(exc) or "status 403" in str(exc)
        raise HTTPException(502, {"code": "llm_error", "message": (
            "The AI service rejected the server's API key. Please ask an administrator to check the configuration."
            if auth_problem else "AI-KEN couldn't reach the AI service. Please try again in a moment.")})


def _store_poem(db: Session, user: User, conv: Conversation, story_msg_id: int | None, result: dict, settings: dict,
                kind: str, parent: int | None) -> Poem:
    p = Poem(user_id=user.id, conversation_id=conv.id, story_message_id=story_msg_id, parent_poem_id=parent,
             title=result["title"], content=result["content"],
             detected_emotions=[e for e in result.get("analysis", {}).get("emotions", [])],
             analysis={k: v for k, v in result.get("analysis", {}).items() if k != "emotions"}
             | {"input_language": result.get("input_language"), "craft_note": result.get("craft_note"),
                "support_note": result.get("support_note")},
             language=result["language"], poem_type=result["form"]["key"], rhyme_scheme=result["rules"].get("rhyme"),
             settings=settings | {"effective_rules": result.get("rules")}, validation=result["validation"],
             vocabulary=result.get("vocabulary"), retrieval=result.get("retrieval"), kind=kind)
    db.add(p)
    db.flush()
    return p


def _assistant_text(result: dict, kind: str) -> str:
    if kind == "regeneration":
        return "Here's another version of your poem."
    if kind == "translation":
        return "Here's your poem in a new language."
    summary = result.get("analysis", {}).get("summary")
    return summary or "Here's a poem shaped from your story."


@router.post("/generate")
def generate(body: GenerateIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _check_quota(db, user)
    s = body.settings
    req = rag.PoemRequest(story=body.story, **s.model_dump())
    result = _run_pipeline(db, req)  # validates/cleans story; raises before anything is stored
    if body.conversation_id:
        conv = _own_conv(db, user, body.conversation_id)
    else:
        title = " ".join(rag.clean_story(body.story, 20000).split()[:7])
        conv = Conversation(user_id=user.id, title=(title[:60] + ("…" if len(title) > 60 else "")) or "New poem")
        db.add(conv)
        db.flush()
    umsg = Message(conversation_id=conv.id, sender="user", content=rag.clean_story(body.story, 20000),
                   meta={"settings": s.model_dump()})
    db.add(umsg)
    db.flush()
    poem = _store_poem(db, user, conv, umsg.id, result, s.model_dump(), "original", None)
    amsg = Message(conversation_id=conv.id, sender="assistant", content=_assistant_text(result, "original"),
                   poem_id=poem.id, meta={"support_note": result.get("support_note")})
    db.add(amsg)
    conv.updated_at = utcnow()
    db.commit()
    po = poem_out(poem)
    return {"conversation": {"id": conv.id, "title": conv.title}, "messages": [message_out(umsg, {}),
                                                                               message_out(amsg, {poem.id: po})]}


@router.post("/poems/{pid}/regenerate")
def regenerate(pid: int, body: RegenerateIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _check_quota(db, user)
    base = _own_poem(db, user, pid)
    story_msg = db.get(Message, base.story_message_id) if base.story_message_id else None
    if not story_msg or story_msg.conversation.user_id != user.id:
        raise HTTPException(400, "The original story for this poem is no longer available.")
    s = body.settings or PoemSettings(**{k: v for k, v in (base.settings or {}).items()
                                          if k in PoemSettings.model_fields})
    if not body.settings:  # keep the same resolved form instead of re-running auto choice
        if s.poem_type == "auto":
            s.poem_type = base.poem_type
        if s.language == "auto":
            s.language = base.language
    req = rag.PoemRequest(story=story_msg.content, variation_of=base.title, **s.model_dump())
    result = _run_pipeline(db, req)
    conv = db.get(Conversation, base.conversation_id)
    poem = _store_poem(db, user, conv, story_msg.id, result, s.model_dump(), "regeneration", base.id)
    note = "Here's another version of your poem." if not body.settings else \
        f"Here's your story as a {result['form']['name']}."
    amsg = Message(conversation_id=conv.id, sender="assistant", content=note, poem_id=poem.id,
                   meta={"action": "regenerate", "from_poem": base.id})
    db.add(amsg)
    conv.updated_at = utcnow()
    db.commit()
    return {"message": message_out(amsg, {poem.id: poem_out(poem)})}


@router.post("/poems/{pid}/translate")
def translate(pid: int, body: TranslateIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _check_quota(db, user)
    base = _own_poem(db, user, pid)
    if body.target == base.language:
        raise HTTPException(400, "The poem is already in that language.")
    form = db.scalar(select(PoetryForm).where(PoetryForm.key == base.poem_type))
    if not form:
        raise HTTPException(400, "This poem's form is no longer available.")
    rules = (base.settings or {}).get("effective_rules") or {}
    try:
        result = rag.translate(db, base.title, base.content, form, rules, body.target, base.language)
    except llm.LLMNotConfigured as exc:
        raise HTTPException(503, {"code": "llm_not_configured", "message": "AI translation is not set up yet.",
                                  "setup_hint": str(exc)})
    except llm.LLMError as exc:
        log.error("Translation failed: %s", exc)
        raise HTTPException(502, {"code": "llm_error", "message": "Translation failed. Please try again."})
    poem = Poem(user_id=user.id, conversation_id=base.conversation_id, story_message_id=base.story_message_id,
                parent_poem_id=base.id, title=result["title"], content=result["content"],
                detected_emotions=base.detected_emotions, analysis=base.analysis, language=body.target,
                poem_type=base.poem_type, rhyme_scheme=base.rhyme_scheme,
                settings=(base.settings or {}) | {"language": body.target}, validation=result["validation"],
                vocabulary=result["vocabulary"], retrieval=base.retrieval, kind="translation")
    db.add(poem)
    db.flush()
    conv = db.get(Conversation, base.conversation_id)
    lang_name = {"fil": "Filipino", "en": "English", "taglish": "Taglish"}[body.target]
    amsg = Message(conversation_id=conv.id, sender="assistant", content=f"Here's your poem in {lang_name}.",
                   poem_id=poem.id, meta={"action": "translate", "from_poem": base.id})
    db.add(amsg)
    conv.updated_at = utcnow()
    db.commit()
    return {"message": message_out(amsg, {poem.id: poem_out(poem)})}


# ---------------- conversations ----------------
@router.get("/conversations")
def list_conversations(q: str | None = Query(None, max_length=100), user: User = Depends(get_current_user),
                       db: Session = Depends(get_db)):
    stmt = select(Conversation).where(Conversation.user_id == user.id)
    if q:
        stmt = stmt.where(Conversation.title.ilike(f"%{q}%"))
    convs = db.scalars(stmt.order_by(Conversation.updated_at.desc()).limit(200)).all()
    return {"conversations": [{"id": c.id, "title": c.title, "updated_at": _iso(c.updated_at)} for c in convs]}


@router.get("/conversations/{cid}")
def get_conversation(cid: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    c = _own_conv(db, user, cid)
    poem_ids = [m.poem_id for m in c.messages if m.poem_id]
    poems = db.scalars(select(Poem).where(Poem.id.in_(poem_ids), Poem.user_id == user.id)).all() if poem_ids else []
    fbs = {f.poem_id: f for f in db.scalars(select(Feedback).where(Feedback.user_id == user.id,
                                                                    Feedback.poem_id.in_(poem_ids)))} if poem_ids else {}
    pmap = {p.id: poem_out(p, fbs.get(p.id)) for p in poems}
    return {"conversation": {"id": c.id, "title": c.title, "created_at": _iso(c.created_at)},
            "messages": [message_out(m, pmap) for m in c.messages]}


@router.patch("/conversations/{cid}")
def rename_conversation(cid: int, body: ConvPatch, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    c = _own_conv(db, user, cid)
    c.title = body.title.strip()
    db.commit()
    return {"conversation": {"id": c.id, "title": c.title}}


@router.delete("/conversations/{cid}")
def delete_conversation(cid: int, keep_saved: bool = False, user: User = Depends(get_current_user),
                        db: Session = Depends(get_db)):
    c = _own_conv(db, user, cid)
    if keep_saved:
        for p in db.scalars(select(Poem).where(Poem.conversation_id == c.id, Poem.is_saved.is_(True))):
            p.conversation_id = None
            p.story_message_id = None
        db.flush()
    db.delete(c)
    db.commit()
    return {"message": "Conversation deleted."}


# ---------------- poems ----------------
@router.get("/poems")
def list_poems(saved: bool = True, q: str | None = Query(None, max_length=100), user: User = Depends(get_current_user),
               db: Session = Depends(get_db)):
    stmt = select(Poem).where(Poem.user_id == user.id)
    if saved:
        stmt = stmt.where(Poem.is_saved.is_(True))
    if q:
        stmt = stmt.where(Poem.title.ilike(f"%{q}%") | Poem.content.ilike(f"%{q}%"))
    poems = db.scalars(stmt.order_by(Poem.created_at.desc()).limit(300)).all()
    return {"poems": [poem_out(p) for p in poems]}


@router.get("/poems/{pid}")
def get_poem(pid: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    p = _own_poem(db, user, pid)
    fb = db.scalar(select(Feedback).where(Feedback.user_id == user.id, Feedback.poem_id == p.id))
    return {"poem": poem_out(p, fb)}


@router.patch("/poems/{pid}")
def update_poem(pid: int, body: PoemPatch, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    p = _own_poem(db, user, pid)
    if body.title is not None:
        p.title = body.title.strip()
    if body.is_saved is not None:
        p.is_saved = body.is_saved
    db.commit()
    return {"poem": poem_out(p)}


@router.delete("/poems/{pid}")
def delete_poem(pid: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    p = _own_poem(db, user, pid)
    for m in db.scalars(select(Message).where(Message.poem_id == p.id)):
        m.poem_id = None
        m.content = "(This poem was deleted.)"
    db.delete(p)
    db.commit()
    return {"message": "Poem deleted."}


@router.post("/poems/{pid}/feedback")
def poem_feedback(pid: int, body: FeedbackIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    p = _own_poem(db, user, pid)
    fb = db.scalar(select(Feedback).where(Feedback.user_id == user.id, Feedback.poem_id == p.id))
    if fb:
        fb.rating, fb.comments = body.rating, (body.comments or None)
    else:
        db.add(Feedback(user_id=user.id, poem_id=p.id, rating=body.rating, comments=body.comments or None))
    db.commit()
    return {"message": "Thank you for your feedback!", "feedback": {"rating": body.rating, "comments": body.comments}}


# ---------------- dictionary & metadata ----------------
@router.get("/dictionary/lookup")
def dictionary_lookup(word: str = Query(min_length=1, max_length=60), language: str | None = None,
                      ai: bool = False, context: str | None = Query(None, max_length=400),
                      user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    limiter.check(f"dict:{user.id}", 60, 60)
    lang = language if language in {"fil", "en", "taglish"} else None
    entry = lookup(db, word.strip(), "en" if lang == "taglish" else lang)
    if entry:
        return {"entry": entry}
    if ai:
        try:
            return {"entry": rag.gloss(word.strip(), lang or detect_language(word)["language"], context)}
        except llm.LLMNotConfigured as exc:
            raise HTTPException(503, {"code": "llm_not_configured", "message": "AI explanations are not configured.",
                                      "setup_hint": str(exc)})
        except llm.LLMError:
            raise HTTPException(502, "The AI service is unavailable right now.")
    return {"entry": None, "message": "No verified dictionary entry was found for this word."}


@router.get("/dictionary/word-of-the-day")
def wotd(language: str | None = None, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not get_setting(db, "show_word_of_day"):
        return {"entry": None}
    return {"entry": word_of_the_day(db, language)}


@router.get("/forms")
def list_forms(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    forms = db.scalars(select(PoetryForm).where(PoetryForm.enabled.is_(True)).order_by(PoetryForm.id)).all()
    return {"forms": [{"key": f.key, "name": f.name, "language": f.language, "tradition": f.tradition,
                       "description": f.description, "rules": {k: v for k, v in f.rules.items()}} for f in forms],
            "emotions": [{"key": k, "label": v} for k, v in EMOTION_LABELS.items()],
            "languages": get_setting(db, "enabled_languages"),
            "max_story_chars": int(get_setting(db, "max_story_chars") or 4000)}


@router.get("/meta/status")
def public_status(db: Session = Depends(get_db)):
    st = llm.llm_status()
    return {"ai_ready": st["configured"], "setup_hint": st["setup_hint"] if not st["configured"] else None,
            "embedding": embedding_status()["provider"], "registration_open": bool(get_setting(db, "registration_open")),
            "max_story_chars": int(get_setting(db, "max_story_chars") or 4000),
            "languages": get_setting(db, "enabled_languages")}
