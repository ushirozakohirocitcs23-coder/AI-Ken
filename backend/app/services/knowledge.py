"""Knowledge-base ingestion: documents, poetry forms and dictionary entries are chunked,
embedded and written to the vector store. Also handles first-run seeding."""
from __future__ import annotations

import io
import re
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import DictionaryEntry, KnowledgeChunk, KnowledgeDocument, PoetryForm
from . import vectorstore
from .embeddings import EmbeddingError

SEED_DIR = Path(__file__).resolve().parent.parent / "seed"


def parse_frontmatter(text: str) -> tuple[dict, str]:
    meta: dict = {}
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, flags=re.S)
    if m:
        for line in m.group(1).splitlines():
            if ":" in line:
                k, _, v = line.partition(":")
                meta[k.strip()] = v.strip()
        text = text[m.end():]
    return meta, text


def extract_text(filename: str, data: bytes) -> str:
    name = filename.lower()
    if name.endswith(".pdf"):
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(data))
        return "\n\n".join((p.extract_text() or "") for p in reader.pages)
    if name.endswith((".txt", ".md", ".markdown", ".csv")):
        for enc in ("utf-8", "utf-8-sig", "latin-1"):
            try:
                return data.decode(enc)
            except UnicodeDecodeError:
                continue
    raise ValueError("Unsupported file type. Upload .txt, .md, .csv or .pdf files.")


def process_document(db: Session, doc: KnowledgeDocument) -> KnowledgeDocument:
    doc.status = "processing"
    db.commit()
    try:
        vectorstore.remove_source(db, "document", doc.id)
        chunks = vectorstore.chunk_text(doc.content)
        if not chunks:
            raise ValueError("The document has no extractable text.")
        texts = [f"[{doc.title}] {c}" for c in chunks]
        vectorstore.add_chunks(db, "document", doc.id, texts, doc.language, doc.doc_type)
        doc.chunk_count = len(chunks)
        doc.status = "ready"
        doc.error = None
        doc.processed_at = datetime.now(timezone.utc)
        db.commit()
    except (EmbeddingError, ValueError) as exc:
        db.rollback()
        doc = db.get(KnowledgeDocument, doc.id)
        doc.status = "error"
        doc.error = str(exc)[:1000]
        db.commit()
    return doc


def form_text(form: PoetryForm) -> str:
    return (f"Poetry form: {form.name} ({form.tradition}, language: {form.language}). {form.description}\n"
            f"Rules: {form.guidance}")


def index_form(db: Session, form: PoetryForm) -> None:
    vectorstore.remove_source(db, "form", form.id)
    lang = form.language if form.language != "any" else "any"
    vectorstore.add_chunks(db, "form", form.id, [form_text(form)], lang, "poetry_rules")


def entry_text(e: DictionaryEntry) -> str:
    parts = [f"{e.word} ({e.part_of_speech or 'word'}, {'Filipino' if e.language == 'fil' else 'English'}): "
             f"{e.definition.rstrip('.')}"]
    if e.synonyms:
        parts.append("Synonyms: " + ", ".join(e.synonyms))
    if e.antonyms:
        parts.append("Antonyms: " + ", ".join(e.antonyms))
    if e.emotion_category:
        parts.append(f"Emotion: {e.emotion_category}")
    if e.example:
        parts.append(f"Example: {e.example}")
    return ". ".join(parts)


def index_entry(db: Session, e: DictionaryEntry) -> None:
    vectorstore.remove_source(db, "dictionary", e.id)
    vectorstore.add_chunks(db, "dictionary", e.id, [entry_text(e)], e.language, e.emotion_category)


def reprocess_all(db: Session) -> dict:
    done = {"documents": 0, "errors": 0, "forms": 0, "dictionary": 0}
    for doc in db.scalars(select(KnowledgeDocument)).all():
        d = process_document(db, doc)
        done["documents" if d.status == "ready" else "errors"] += 1
    for form in db.scalars(select(PoetryForm)).all():
        index_form(db, form)
        done["forms"] += 1
    for e in db.scalars(select(DictionaryEntry)).all():
        index_entry(db, e)
        done["dictionary"] += 1
    db.commit()
    return done


def seed(db: Session) -> dict:
    """Idempotent first-run seeding of forms, dictionary and knowledge documents."""
    from ..seed.dictionary import ENGLISH, FILIPINO, SOURCE
    from ..seed.forms import FORMS
    created = {"forms": 0, "dictionary": 0, "documents": 0}
    for f in FORMS:
        if not db.scalar(select(PoetryForm).where(PoetryForm.key == f["key"])):
            form = PoetryForm(**f)
            db.add(form)
            db.flush()
            index_form(db, form)
            created["forms"] += 1
    for lang, rows in (("fil", FILIPINO), ("en", ENGLISH)):
        for word, pos, definition, syn, ant, ex, emo, level, lit in rows:
            if db.scalar(select(DictionaryEntry).where(DictionaryEntry.word == word, DictionaryEntry.language == lang)):
                continue
            e = DictionaryEntry(word=word, language=lang, part_of_speech=pos, definition=definition, synonyms=syn,
                                antonyms=ant, example=ex, emotion_category=emo, level=level, literary_usage=lit,
                                source=SOURCE, verified=False)
            db.add(e)
            db.flush()
            index_entry(db, e)
            created["dictionary"] += 1
    db.commit()
    for path in sorted((SEED_DIR / "knowledge").glob("*.md")):
        meta, body = parse_frontmatter(path.read_text(encoding="utf-8"))
        title = meta.get("title", path.stem)
        if db.scalar(select(KnowledgeDocument).where(KnowledgeDocument.title == title)):
            continue
        doc = KnowledgeDocument(title=title, source=meta.get("source"), language=meta.get("language", "en"),
                                doc_type=meta.get("doc_type", "reference"), content=body.strip(), is_system=True,
                                content_meta={"filename": path.name, "chars": len(body)})
        db.add(doc)
        db.commit()
        process_document(db, doc)
        created["documents"] += 1
    return created


def ensure_index_current(db: Session) -> None:
    """If the embedding model changed since the last run, re-embed everything."""
    st = vectorstore.stats(db)
    if st["stale_chunks"] > 0 or (st["total_chunks"] == 0 and db.scalar(select(func.count(PoetryForm.id)))):
        reprocess_all(db)
        db.query(KnowledgeChunk).filter(KnowledgeChunk.embedding_model != st["embedding_model"]).delete()
        db.commit()
