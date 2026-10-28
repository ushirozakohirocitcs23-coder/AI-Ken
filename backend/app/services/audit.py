from __future__ import annotations

from sqlalchemy.orm import Session

from ..models import AuditLog, RagLog


def audit(db: Session, action: str, actor_id: int | None = None, target: str | None = None,
          meta: dict | None = None, ip: str | None = None, commit: bool = True) -> None:
    """Record a security/admin event. Never pass story text, poems, or passwords in meta."""
    db.add(AuditLog(actor_id=actor_id, action=action, target=target, meta=meta, ip=ip))
    if commit:
        db.commit()


def rag_log(db: Session, stage: str, ok: bool, latency_ms: int, result_count: int | None = None,
            top_score: float | None = None, detail: str | None = None) -> None:
    db.add(RagLog(stage=stage, ok=ok, latency_ms=latency_ms, result_count=result_count, top_score=top_score,
                  detail=(detail or "")[:500] or None))
