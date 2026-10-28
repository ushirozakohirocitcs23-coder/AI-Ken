"""Administrator module. Every route depends on require_admin (server-side role check).

Privacy: no endpoint here returns users' stories, messages or poem text. Analytics are
aggregate counts only."""
from __future__ import annotations

import time
from collections import Counter
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import (AuditLog, Conversation, DictionaryEntry, Feedback, KnowledgeDocument, Poem, PoetryForm,
                      RagLog, User, UserSession)
from ..security import PASSWORD_RULE, client_ip, hash_password, password_ok, require_admin, revoke_all_sessions
from ..services import llm, vectorstore
from ..services.audit import audit
from ..services.dictionary import entry_dict
from ..services.embeddings import embedding_status
from ..services.knowledge import extract_text, index_entry, index_form, process_document, reprocess_all
from ..services.language import EMOTION_LABELS
from ..services.settings_store import DEFAULTS, DESCRIPTIONS, all_settings, set_setting

router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(require_admin)])


def _iso(dt):
    return dt.isoformat() if dt else None


def _since(days: int):
    return datetime.now(timezone.utc) - timedelta(days=days)


# ---------------- overview & health ----------------
@router.get("/overview")
def overview(db: Session = Depends(get_db)):
    count = lambda stmt: db.scalar(stmt) or 0  # noqa: E731
    users_total = count(select(func.count(User.id)))
    by_status = dict(db.execute(select(User.status, func.count(User.id)).group_by(User.status)).all())
    active_7d = count(select(func.count(User.id)).where(User.last_login_at >= _since(7)))
    fb_avg = db.scalar(select(func.avg(Feedback.rating)))
    recent = db.scalars(select(AuditLog).order_by(AuditLog.id.desc()).limit(8)).all()
    names = {u.id: u.full_name for u in db.scalars(select(User).where(User.id.in_([a.actor_id for a in recent if a.actor_id])))}
    return {
        "users": {"total": users_total, "active": by_status.get("active", 0), "inactive": by_status.get("inactive", 0),
                  "suspended": by_status.get("suspended", 0), "admins": count(select(func.count(User.id)).where(User.role == "admin")),
                  "logged_in_last_7d": active_7d, "new_last_7d": count(select(func.count(User.id)).where(User.created_at >= _since(7)))},
        "poems": {"total": count(select(func.count(Poem.id))), "last_7d": count(select(func.count(Poem.id)).where(Poem.created_at >= _since(7))),
                  "saved": count(select(func.count(Poem.id)).where(Poem.is_saved.is_(True)))},
        "conversations": count(select(func.count(Conversation.id))),
        "feedback": {"count": count(select(func.count(Feedback.id))), "average": round(float(fb_avg), 2) if fb_avg else None},
        "recent_activity": [{"action": a.action, "actor": names.get(a.actor_id), "target": a.target,
                             "at": _iso(a.created_at)} for a in recent],
        "services": health(db),
    }


@router.get("/health")
def health(db: Session = Depends(get_db)):
    llm_st = llm.llm_status()
    emb = embedding_status()
    vs = vectorstore.stats(db)
    since = _since(1)
    stages = {}
    for stage in ("analysis", "retrieval", "generation", "validation", "translation"):
        total = db.scalar(select(func.count(RagLog.id)).where(RagLog.stage == stage, RagLog.created_at >= since)) or 0
        failed = db.scalar(select(func.count(RagLog.id)).where(RagLog.stage == stage, RagLog.created_at >= since,
                                                               RagLog.ok.is_(False))) or 0
        stages[stage] = {"last_24h": total, "failed": failed}
    t0 = time.monotonic()
    try:
        vectorstore.search(db, "tanaga pantig tugma", k=1)
        rag_ok, rag_err = True, None
    except Exception as exc:  # pragma: no cover
        rag_ok, rag_err = False, str(exc)[:200]
    return {"ai": llm_st, "embeddings": emb, "vector_store": vs | {"ok": rag_ok and vs["chunks_current_model"] > 0,
                                                                     "error": rag_err,
                                                                     "probe_ms": int((time.monotonic() - t0) * 1000)},
            "pipeline_24h": stages, "database": {"ok": True}}


# ---------------- users ----------------
class UserPatch(BaseModel):
    status: str | None = Field(None, pattern="^(active|inactive|suspended)$")
    role: str | None = Field(None, pattern="^(user|admin)$")


class AdminCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str


def user_row(u: User, poems: int = 0) -> dict:
    return {"id": u.id, "full_name": u.full_name, "email": u.email, "role": u.role, "status": u.status,
            "created_at": _iso(u.created_at), "last_login_at": _iso(u.last_login_at), "poem_count": poems}


@router.get("/users")
def list_users(q: str | None = Query(None, max_length=100), role: str | None = None, status: str | None = None,
               page: int = Query(1, ge=1), per_page: int = Query(20, ge=1, le=100), db: Session = Depends(get_db)):
    stmt = select(User)
    if q:
        stmt = stmt.where(or_(User.full_name.ilike(f"%{q}%"), User.email.ilike(f"%{q}%")))
    if role in {"user", "admin"}:
        stmt = stmt.where(User.role == role)
    if status in {"active", "inactive", "suspended"}:
        stmt = stmt.where(User.status == status)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    users = db.scalars(stmt.order_by(User.created_at.desc()).offset((page - 1) * per_page).limit(per_page)).all()
    counts = dict(db.execute(select(Poem.user_id, func.count(Poem.id)).where(Poem.user_id.in_([u.id for u in users]))
                             .group_by(Poem.user_id)).all()) if users else {}
    return {"users": [user_row(u, counts.get(u.id, 0)) for u in users], "total": total, "page": page, "per_page": per_page}


@router.patch("/users/{uid}")
def update_user(uid: int, body: UserPatch, request: Request, admin: User = Depends(require_admin),
                db: Session = Depends(get_db)):
    u = db.get(User, uid)
    if not u:
        raise HTTPException(404, "User not found.")
    if u.id == admin.id and (body.role == "user" or (body.status and body.status != "active")):
        raise HTTPException(400, "You cannot demote or deactivate your own account.")
    changes = {}
    if body.role and body.role != u.role:
        if u.role == "admin" and body.role == "user":
            admins = db.scalar(select(func.count(User.id)).where(User.role == "admin", User.status == "active")) or 0
            if admins <= 1:
                raise HTTPException(400, "At least one active administrator is required.")
        changes["role"] = [u.role, body.role]
        u.role = body.role
    if body.status and body.status != u.status:
        changes["status"] = [u.status, body.status]
        u.status = body.status
        if body.status != "active":
            revoke_all_sessions(db, u.id)
    db.commit()
    if changes:
        audit(db, "admin.user_updated", admin.id, f"user:{u.id}", changes, client_ip(request))
    return {"user": user_row(u)}


@router.delete("/users/{uid}")
def delete_user(uid: int, request: Request, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    u = db.get(User, uid)
    if not u:
        raise HTTPException(404, "User not found.")
    if u.id == admin.id:
        raise HTTPException(400, "You cannot delete your own account here.")
    if u.role == "admin":
        admins = db.scalar(select(func.count(User.id)).where(User.role == "admin")) or 0
        if admins <= 1:
            raise HTTPException(400, "Cannot delete the last administrator.")
    email = u.email
    db.delete(u)
    db.commit()
    audit(db, "admin.user_deleted", admin.id, f"user:{uid}", {"email": email}, client_ip(request))
    return {"message": "Account deleted."}


@router.post("/users/admins", status_code=201)
def create_admin(body: AdminCreate, request: Request, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    if not password_ok(body.password):
        raise HTTPException(422, PASSWORD_RULE)
    email = body.email.lower().strip()
    if db.scalar(select(User).where(func.lower(User.email) == email)):
        raise HTTPException(409, "An account with this email already exists.")
    u = User(full_name=body.full_name.strip(), email=email, password_hash=hash_password(body.password), role="admin")
    db.add(u)
    db.commit()
    audit(db, "admin.admin_created", admin.id, f"user:{u.id}", {"email": email}, client_ip(request))
    return {"user": user_row(u)}


# ---------------- knowledge base ----------------
class DocPatch(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=200)
    source: str | None = Field(None, max_length=500)
    language: str | None = Field(None, pattern="^(fil|en|any)$")
    doc_type: str | None = Field(None, pattern="^(poetry_rules|technique|vocabulary|reference|guideline)$")
    content: str | None = Field(None, min_length=1, max_length=500000)


def doc_out(d: KnowledgeDocument, full: bool = False) -> dict:
    out = {"id": d.id, "title": d.title, "source": d.source, "language": d.language, "doc_type": d.doc_type,
           "status": d.status, "error": d.error, "chunk_count": d.chunk_count, "is_system": d.is_system,
           "uploaded_at": _iso(d.uploaded_at), "processed_at": _iso(d.processed_at),
           "chars": len(d.content or ""), "meta": d.content_meta}
    if full:
        out["content"] = d.content
    return out


@router.get("/knowledge")
def list_docs(db: Session = Depends(get_db)):
    docs = db.scalars(select(KnowledgeDocument).order_by(KnowledgeDocument.uploaded_at.desc())).all()
    return {"documents": [doc_out(d) for d in docs], "stats": vectorstore.stats(db)}


@router.get("/knowledge/{did}")
def get_doc(did: int, db: Session = Depends(get_db)):
    d = db.get(KnowledgeDocument, did)
    if not d:
        raise HTTPException(404, "Document not found.")
    return {"document": doc_out(d, full=True)}


@router.post("/knowledge", status_code=201)
async def upload_doc(request: Request, file: UploadFile | None = File(None), text: str | None = Form(None),
                     title: str = Form(..., min_length=1, max_length=200), source: str | None = Form(None),
                     language: str = Form("en"), doc_type: str = Form("reference"),
                     admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    if language not in {"fil", "en", "any"} or doc_type not in {"poetry_rules", "technique", "vocabulary", "reference",
                                                                 "guideline"}:
        raise HTTPException(422, "Invalid language or document type.")
    if file is not None and file.filename:
        data = await file.read()
        if len(data) > 10 * 1024 * 1024:
            raise HTTPException(413, "File too large (max 10 MB).")
        try:
            content = extract_text(file.filename, data)
        except ValueError as exc:
            raise HTTPException(415, str(exc))
        except Exception:
            raise HTTPException(422, "Could not read this file. Is it a valid PDF/text file?")
        meta = {"filename": file.filename, "bytes": len(data)}
    elif text:
        content, meta = text, {"pasted": True}
    else:
        raise HTTPException(422, "Upload a file or paste text.")
    content = content.replace("\x00", "").strip()
    if not content:
        raise HTTPException(422, "The document has no readable text.")
    doc = KnowledgeDocument(title=title.strip(), source=(source or "").strip() or None, language=language,
                            doc_type=doc_type, content=content, content_meta=meta | {"chars": len(content)},
                            uploaded_by=admin.id)
    db.add(doc)
    db.commit()
    doc = process_document(db, doc)
    audit(db, "admin.kb_uploaded", admin.id, f"doc:{doc.id}", {"title": doc.title, "status": doc.status},
          client_ip(request))
    return {"document": doc_out(doc)}


@router.patch("/knowledge/{did}")
def update_doc(did: int, body: DocPatch, request: Request, admin: User = Depends(require_admin),
               db: Session = Depends(get_db)):
    d = db.get(KnowledgeDocument, did)
    if not d:
        raise HTTPException(404, "Document not found.")
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(d, k, v.strip() if isinstance(v, str) else v)
    db.commit()
    d = process_document(db, d)
    audit(db, "admin.kb_updated", admin.id, f"doc:{d.id}", {"fields": list(body.model_dump(exclude_none=True))},
          client_ip(request))
    return {"document": doc_out(d)}


@router.delete("/knowledge/{did}")
def delete_doc(did: int, request: Request, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    d = db.get(KnowledgeDocument, did)
    if not d:
        raise HTTPException(404, "Document not found.")
    vectorstore.remove_source(db, "document", d.id)
    db.delete(d)
    db.commit()
    audit(db, "admin.kb_deleted", admin.id, f"doc:{did}", {"title": d.title}, client_ip(request))
    return {"message": "Document removed from the knowledge base."}


@router.post("/knowledge/{did}/reprocess")
def reprocess_doc(did: int, request: Request, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    d = db.get(KnowledgeDocument, did)
    if not d:
        raise HTTPException(404, "Document not found.")
    d = process_document(db, d)
    audit(db, "admin.kb_reprocessed", admin.id, f"doc:{d.id}", ip=client_ip(request))
    return {"document": doc_out(d)}


@router.post("/knowledge/reprocess-all")
def reprocess_everything(request: Request, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    t0 = time.monotonic()
    result = reprocess_all(db)
    audit(db, "admin.kb_reprocessed_all", admin.id, meta=result, ip=client_ip(request))
    return {"result": result, "seconds": round(time.monotonic() - t0, 2), "stats": vectorstore.stats(db)}


class SearchTest(BaseModel):
    query: str = Field(min_length=2, max_length=500)
    source_type: str | None = Field(None, pattern="^(document|dictionary|form)$")
    k: int = Field(5, ge=1, le=20)


@router.post("/knowledge/search-test")
def search_test(body: SearchTest, db: Session = Depends(get_db)):
    t0 = time.monotonic()
    hits = vectorstore.search(db, body.query, k=body.k, source_types={body.source_type} if body.source_type else None,
                              min_score=0.0)
    return {"latency_ms": int((time.monotonic() - t0) * 1000),
            "hits": [{"source_type": h.source_type, "source_id": h.source_id, "language": h.language,
                      "category": h.category, "score": round(h.score, 4), "text": h.text[:400]} for h in hits]}


@router.get("/rag-logs")
def rag_logs(stage: str | None = None, only_errors: bool = False, limit: int = Query(100, le=500),
             db: Session = Depends(get_db)):
    stmt = select(RagLog)
    if stage:
        stmt = stmt.where(RagLog.stage == stage)
    if only_errors:
        stmt = stmt.where(RagLog.ok.is_(False))
    logs = db.scalars(stmt.order_by(RagLog.id.desc()).limit(limit)).all()
    agg = db.execute(select(RagLog.stage, func.count(RagLog.id), func.avg(RagLog.latency_ms), func.avg(RagLog.top_score))
                     .where(RagLog.created_at >= _since(7)).group_by(RagLog.stage)).all()
    return {"logs": [{"id": l.id, "stage": l.stage, "ok": l.ok, "latency_ms": l.latency_ms, "result_count": l.result_count,
                      "top_score": l.top_score, "detail": l.detail, "at": _iso(l.created_at)} for l in logs],
            "summary_7d": [{"stage": s, "count": c, "avg_latency_ms": round(float(a or 0)),
                            "avg_top_score": round(float(t), 3) if t is not None else None} for s, c, a, t in agg]}


# ---------------- poetry forms ----------------
class FormPatch(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=80)
    description: str | None = Field(None, max_length=2000)
    guidance: str | None = Field(None, max_length=5000)
    rules: dict | None = None
    source_references: str | None = Field(None, max_length=2000)
    enabled: bool | None = None


ALLOWED_RULE_KEYS = {"lines", "lines_min", "lines_max", "lines_multiple_of", "syllables", "syllables_per_line",
                     "syllable_tolerance", "syllable_mode", "syllable_label", "rhyme", "rhyme_alternatives",
                     "rhyme_repeat", "rhyme_per_stanza", "acrostic", "words_per_line", "stanza_size", "stanza_label",
                     "locked", "controls"}


@router.get("/forms")
def admin_forms(db: Session = Depends(get_db)):
    forms = db.scalars(select(PoetryForm).order_by(PoetryForm.id)).all()
    return {"forms": [{"id": f.id, "key": f.key, "name": f.name, "language": f.language, "tradition": f.tradition,
                       "description": f.description, "guidance": f.guidance, "rules": f.rules,
                       "source_references": f.source_references, "enabled": f.enabled,
                       "updated_at": _iso(f.updated_at)} for f in forms]}


@router.patch("/forms/{fid}")
def update_form(fid: int, body: FormPatch, request: Request, admin: User = Depends(require_admin),
                db: Session = Depends(get_db)):
    f = db.get(PoetryForm, fid)
    if not f:
        raise HTTPException(404, "Form not found.")
    data = body.model_dump(exclude_none=True)
    if "rules" in data:
        bad = set(data["rules"]) - ALLOWED_RULE_KEYS
        if bad:
            raise HTTPException(422, f"Unknown rule keys: {', '.join(sorted(bad))}")
    for k, v in data.items():
        setattr(f, k, v)
    db.commit()
    index_form(db, f)
    db.commit()
    audit(db, "admin.form_updated", admin.id, f"form:{f.key}", {"fields": list(data)}, client_ip(request))
    return {"form": {"id": f.id, "key": f.key, "enabled": f.enabled}}


# ---------------- dictionary ----------------
class EntryIn(BaseModel):
    word: str = Field(min_length=1, max_length=80)
    language: str = Field(pattern="^(fil|en)$")
    part_of_speech: str | None = Field(None, max_length=40)
    definition: str = Field(min_length=2, max_length=2000)
    synonyms: list[str] = Field(default_factory=list)
    antonyms: list[str] = Field(default_factory=list)
    example: str | None = Field(None, max_length=1000)
    emotion_category: str | None = None
    literary_usage: str | None = Field(None, max_length=1000)
    level: str = Field("intermediate", pattern="^(simple|intermediate|advanced)$")
    source: str = Field(min_length=2, max_length=300)
    source_url: str | None = Field(None, max_length=500)
    verified: bool = False


@router.get("/dictionary")
def list_entries(q: str | None = Query(None, max_length=80), language: str | None = None, verified: bool | None = None,
                 page: int = Query(1, ge=1), per_page: int = Query(25, ge=1, le=100), db: Session = Depends(get_db)):
    stmt = select(DictionaryEntry)
    if q:
        stmt = stmt.where(or_(DictionaryEntry.word.ilike(f"%{q}%"), DictionaryEntry.definition.ilike(f"%{q}%")))
    if language in {"fil", "en"}:
        stmt = stmt.where(DictionaryEntry.language == language)
    if verified is not None:
        stmt = stmt.where(DictionaryEntry.verified.is_(verified))
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(stmt.order_by(DictionaryEntry.word).offset((page - 1) * per_page).limit(per_page)).all()
    return {"entries": [entry_dict(e) for e in rows], "total": total, "page": page, "per_page": per_page}


def _check_emotion(cat: str | None):
    if cat and cat not in EMOTION_LABELS:
        raise HTTPException(422, "Unknown emotion category.")


@router.post("/dictionary", status_code=201)
def create_entry(body: EntryIn, request: Request, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    _check_emotion(body.emotion_category)
    word = body.word.strip().lower()
    if db.scalar(select(DictionaryEntry).where(DictionaryEntry.word == word, DictionaryEntry.language == body.language)):
        raise HTTPException(409, "This word already exists for that language.")
    e = DictionaryEntry(**(body.model_dump() | {"word": word}))
    db.add(e)
    db.commit()
    index_entry(db, e)
    db.commit()
    audit(db, "admin.dictionary_created", admin.id, f"entry:{e.id}", {"word": word}, client_ip(request))
    return {"entry": entry_dict(e)}


@router.put("/dictionary/{eid}")
def update_entry(eid: int, body: EntryIn, request: Request, admin: User = Depends(require_admin),
                 db: Session = Depends(get_db)):
    _check_emotion(body.emotion_category)
    e = db.get(DictionaryEntry, eid)
    if not e:
        raise HTTPException(404, "Entry not found.")
    for k, v in body.model_dump().items():
        setattr(e, k, v.strip().lower() if k == "word" else v)
    db.commit()
    index_entry(db, e)
    db.commit()
    audit(db, "admin.dictionary_updated", admin.id, f"entry:{e.id}", {"word": e.word, "verified": e.verified},
          client_ip(request))
    return {"entry": entry_dict(e)}


@router.delete("/dictionary/{eid}")
def delete_entry(eid: int, request: Request, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    e = db.get(DictionaryEntry, eid)
    if not e:
        raise HTTPException(404, "Entry not found.")
    vectorstore.remove_source(db, "dictionary", e.id)
    db.delete(e)
    db.commit()
    audit(db, "admin.dictionary_deleted", admin.id, f"entry:{eid}", {"word": e.word}, client_ip(request))
    return {"message": "Entry deleted."}


# ---------------- analytics ----------------
@router.get("/analytics")
def analytics(days: int = Query(30, ge=7, le=365), db: Session = Depends(get_db)):
    since = _since(days)
    rows = db.execute(select(Poem.created_at, Poem.poem_type, Poem.language, Poem.kind, Poem.detected_emotions,
                             Poem.validation).where(Poem.created_at >= since)).all()
    per_day: Counter = Counter()
    forms: Counter = Counter()
    langs: Counter = Counter()
    kinds: Counter = Counter()
    emotions: Counter = Counter()
    validation: Counter = Counter()
    for created, ptype, lang, kind, emos, val in rows:
        per_day[(created if created.tzinfo else created.replace(tzinfo=timezone.utc)).date().isoformat()] += 1
        forms[ptype] += 1
        langs[lang] += 1
        kinds[kind] += 1
        validation[(val or {}).get("overall", "unknown")] += 1
        for e in (emos or [])[:3]:
            if isinstance(e, dict) and e.get("emotion"):
                emotions[e["emotion"]] += 1
    today = datetime.now(timezone.utc).date()
    series = [{"date": (today - timedelta(days=i)).isoformat(),
               "poems": per_day.get((today - timedelta(days=i)).isoformat(), 0)} for i in range(days - 1, -1, -1)]
    form_names = dict(db.execute(select(PoetryForm.key, PoetryForm.name)).all())
    ratings = dict(db.execute(select(Feedback.rating, func.count(Feedback.id)).group_by(Feedback.rating)).all())
    avg = db.scalar(select(func.avg(Feedback.rating)))
    signups = db.execute(select(User.created_at).where(User.created_at >= since)).scalars().all()
    su: Counter = Counter((d if d.tzinfo else d.replace(tzinfo=timezone.utc)).date().isoformat() for d in signups)
    return {
        "days": days,
        "poems_by_date": [s | {"signups": su.get(s["date"], 0)} for s in series],
        "forms": [{"key": k, "name": form_names.get(k, k), "count": c} for k, c in forms.most_common()],
        "languages": [{"language": k, "count": c} for k, c in langs.most_common()],
        "kinds": dict(kinds),
        "emotions": [{"emotion": k, "label": EMOTION_LABELS.get(k, k), "count": c} for k, c in emotions.most_common()],
        "validation": dict(validation),
        "ratings": {"distribution": {str(i): ratings.get(i, 0) for i in range(1, 6)},
                    "average": round(float(avg), 2) if avg else None, "count": sum(ratings.values())},
    }


# ---------------- settings ----------------
class SettingsIn(BaseModel):
    values: dict


@router.get("/settings")
def get_settings(db: Session = Depends(get_db)):
    return {"settings": all_settings(db), "descriptions": DESCRIPTIONS}


@router.put("/settings")
def put_settings(body: SettingsIn, request: Request, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    changed = {}
    for k, v in body.values.items():
        if k not in DEFAULTS:
            raise HTTPException(422, f"Unknown setting: {k}")
        d = DEFAULTS[k]
        if isinstance(d, bool):
            if not isinstance(v, bool):
                raise HTTPException(422, f"{k} must be true/false.")
        elif isinstance(d, int):
            if not isinstance(v, int) or isinstance(v, bool) or v < 0 or v > 100000:
                raise HTTPException(422, f"{k} must be a non-negative whole number.")
            if k == "max_revision_attempts" and v > 4:
                raise HTTPException(422, "max_revision_attempts must be between 0 and 4.")
            if k == "retrieval_top_k" and not 1 <= v <= 20:
                raise HTTPException(422, "retrieval_top_k must be between 1 and 20.")
            if k == "max_story_chars" and not 200 <= v <= 20000:
                raise HTTPException(422, "max_story_chars must be between 200 and 20000.")
        elif k == "enabled_languages":
            if not isinstance(v, list) or not v or not set(v) <= {"fil", "en", "taglish"}:
                raise HTTPException(422, "enabled_languages must be a non-empty subset of fil, en, taglish.")
        set_setting(db, k, v)
        changed[k] = v
    db.commit()
    audit(db, "admin.settings_updated", admin.id, meta=changed, ip=client_ip(request))
    return {"settings": all_settings(db)}


# ---------------- audit logs ----------------
@router.get("/audit-logs")
def audit_logs(action: str | None = Query(None, max_length=80), page: int = Query(1, ge=1),
               per_page: int = Query(50, ge=1, le=200), db: Session = Depends(get_db)):
    stmt = select(AuditLog)
    if action:
        stmt = stmt.where(AuditLog.action.ilike(f"%{action}%"))
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    logs = db.scalars(stmt.order_by(AuditLog.id.desc()).offset((page - 1) * per_page).limit(per_page)).all()
    actor_ids = {l.actor_id for l in logs if l.actor_id}
    actors = {u.id: u.email for u in db.scalars(select(User).where(User.id.in_(actor_ids)))} if actor_ids else {}
    return {"logs": [{"id": l.id, "action": l.action, "actor_id": l.actor_id, "actor": actors.get(l.actor_id),
                      "target": l.target, "meta": l.meta, "ip": l.ip, "at": _iso(l.created_at)} for l in logs],
            "total": total, "page": page}


@router.get("/sessions/active")
def active_sessions(db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc)
    return {"active_sessions": db.scalar(select(func.count(UserSession.id)).where(UserSession.expires_at > now)) or 0}
