"""Authentication primitives: password hashing, server-side sessions, role guards,
CSRF header check and a small in-memory rate limiter."""
from __future__ import annotations

import hashlib
import re
import secrets
import threading
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import Depends, HTTPException, Request, Response, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from .config import settings
from .database import get_db
from .models import User, UserSession

SESSION_COOKIE = "aiken_session"
PASSWORD_RULE = "Password must be at least 8 characters and include a letter and a number."


# ---------- passwords ----------
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8")[:72], bcrypt.gensalt(rounds=12)).decode()


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8")[:72], hashed.encode())
    except ValueError:
        return False


def password_ok(password: str) -> bool:
    return (len(password) >= 8 and len(password) <= 128 and re.search(r"[A-Za-z]", password) is not None
            and re.search(r"\d", password) is not None)


def sha256(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _as_aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


# ---------- sessions ----------
def create_session(db: Session, user: User, response: Response, user_agent: str | None) -> None:
    token = secrets.token_urlsafe(32)
    expires = datetime.now(timezone.utc) + timedelta(days=settings.session_days)
    db.add(UserSession(user_id=user.id, token_hash=sha256(token), expires_at=expires,
                       user_agent=(user_agent or "")[:255]))
    db.commit()
    response.set_cookie(SESSION_COOKIE, token, httponly=True, secure=settings.cookie_secure, samesite="lax",
                        max_age=settings.session_days * 86400, path="/")


def destroy_session(db: Session, request: Request, response: Response) -> None:
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        db.execute(delete(UserSession).where(UserSession.token_hash == sha256(token)))
        db.commit()
    response.delete_cookie(SESSION_COOKIE, path="/")


def revoke_all_sessions(db: Session, user_id: int) -> None:
    db.execute(delete(UserSession).where(UserSession.user_id == user_id))


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    sess = db.scalar(select(UserSession).where(UserSession.token_hash == sha256(token)))
    if not sess or _as_aware(sess.expires_at) < datetime.now(timezone.utc):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Session expired. Please log in again.")
    user = db.get(User, sess.user_id)
    if not user or user.status != "active":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This account is not active.")
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Administrator access required.")
    return user


# ---------- CSRF ----------
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


async def csrf_guard(request: Request) -> None:
    """Mutating API calls must carry X-Requested-With. Browsers cannot attach this
    header cross-site without a CORS preflight, which our CORS policy rejects."""
    if request.method not in SAFE_METHODS and request.url.path.startswith("/api/"):
        if request.headers.get("x-requested-with") != "AI-KEN":
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Missing CSRF header.")


# ---------- rate limiting ----------
class RateLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, key: str, limit: int, window_s: int) -> None:
        now = time.monotonic()
        with self._lock:
            q = self._hits[key]
            while q and now - q[0] > window_s:
                q.popleft()
            if len(q) >= limit:
                retry = int(window_s - (now - q[0])) + 1
                raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS,
                                    f"Too many requests. Please try again in {retry} seconds.")
            q.append(now)

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


limiter = RateLimiter()


def client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"
