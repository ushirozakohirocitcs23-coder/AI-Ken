from __future__ import annotations

import logging
import secrets
import smtplib
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..models import Conversation, PasswordReset, Poem, User, utcnow
from ..security import (PASSWORD_RULE, _as_aware, client_ip, create_session, destroy_session, get_current_user,
                        hash_password, limiter, password_ok, revoke_all_sessions, sha256, verify_password)
from ..services.audit import audit
from ..services.settings_store import get_setting

router = APIRouter(prefix="/api", tags=["auth"])
log = logging.getLogger("aiken.auth")


class RegisterIn(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)
    confirm_password: str


class LoginIn(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=128)


class ForgotIn(BaseModel):
    email: str = Field(min_length=3, max_length=255)


class ResetIn(BaseModel):
    token: str = Field(min_length=10, max_length=200)
    password: str
    confirm_password: str


class ProfileIn(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)


class PasswordIn(BaseModel):
    current_password: str
    new_password: str
    confirm_password: str


def user_out(u: User) -> dict:
    return {"id": u.id, "full_name": u.full_name, "email": u.email, "role": u.role, "status": u.status,
            "created_at": u.created_at.isoformat() if u.created_at else None}


@router.post("/auth/register", status_code=201)
def register(body: RegisterIn, request: Request, response: Response, db: Session = Depends(get_db)):
    limiter.check(f"register:{client_ip(request)}", 10, 3600)
    if not get_setting(db, "registration_open"):
        raise HTTPException(403, "Registration is currently closed.")
    name = " ".join(body.full_name.split())
    if len(name) < 2:
        raise HTTPException(422, "Please enter your full name.")
    if body.password != body.confirm_password:
        raise HTTPException(422, "Passwords do not match.")
    if not password_ok(body.password):
        raise HTTPException(422, PASSWORD_RULE)
    email = body.email.lower().strip()
    if db.scalar(select(User).where(func.lower(User.email) == email)):
        raise HTTPException(409, "An account with this email already exists.")
    # Public registration ALWAYS creates a regular user. Role is never read from the request.
    user = User(full_name=name, email=email, password_hash=hash_password(body.password), role="user", status="active")
    db.add(user)
    db.commit()
    audit(db, "user.register", user.id, f"user:{user.id}", ip=client_ip(request))
    create_session(db, user, response, request.headers.get("user-agent"))
    return {"user": user_out(user), "message": "Welcome to AI-KEN! Your account has been created."}


@router.post("/auth/login")
def login(body: LoginIn, request: Request, response: Response, db: Session = Depends(get_db)):
    ip = client_ip(request)
    email = body.email.lower().strip()
    limiter.check(f"login:{ip}", 20, 300)
    limiter.check(f"login:{email}", 8, 300)
    user = db.scalar(select(User).where(func.lower(User.email) == email))
    if not user or not verify_password(body.password, user.password_hash):
        audit(db, "auth.login_failed", user.id if user else None, meta={"reason": "bad_credentials"}, ip=ip)
        raise HTTPException(401, "Incorrect email or password.")
    if user.status != "active":
        audit(db, "auth.login_blocked", user.id, meta={"status": user.status}, ip=ip)
        raise HTTPException(403, f"This account is {user.status}. Please contact the administrator.")
    user.last_login_at = utcnow()
    db.commit()
    create_session(db, user, response, request.headers.get("user-agent"))
    audit(db, "auth.login", user.id, ip=ip)
    return {"user": user_out(user), "redirect": "/admin" if user.role == "admin" else "/app"}


@router.post("/auth/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    destroy_session(db, request, response)
    return {"message": "You have been logged out."}


@router.get("/auth/me")
def me(user: User = Depends(get_current_user)):
    return {"user": user_out(user)}


def _send_reset_email(to: str, link: str) -> bool:
    if not settings.smtp_host:
        return False
    msg = EmailMessage()
    msg["Subject"] = "Reset your AI-KEN password"
    msg["From"] = settings.smtp_from
    msg["To"] = to
    msg.set_content(f"Hello,\n\nUse this link within 30 minutes to reset your AI-KEN password:\n{link}\n\n"
                    "If you did not request this, you can ignore this email.\n\n— AI-KEN")
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as s:
            s.starttls()
            if settings.smtp_user:
                s.login(settings.smtp_user, settings.smtp_password)
            s.send_message(msg)
        return True
    except (OSError, smtplib.SMTPException) as exc:
        log.error("Password reset email failed: %s", exc)
        return False


@router.post("/auth/forgot-password")
def forgot_password(body: ForgotIn, request: Request, db: Session = Depends(get_db)):
    limiter.check(f"forgot:{client_ip(request)}", 5, 3600)
    generic = {"message": "If an account exists for that email, a password reset link has been sent."}
    user = db.scalar(select(User).where(func.lower(User.email) == body.email.lower().strip()))
    if not user or user.status != "active":
        return generic
    token = secrets.token_urlsafe(32)
    db.add(PasswordReset(user_id=user.id, token_hash=sha256(token),
                         expires_at=datetime.now(timezone.utc) + timedelta(minutes=30)))
    db.commit()
    link = f"{settings.public_url.rstrip('/')}/reset-password?token={token}"
    sent = _send_reset_email(user.email, link)
    audit(db, "auth.password_reset_requested", user.id, meta={"email_sent": sent}, ip=client_ip(request))
    if not sent:
        log.warning("SMTP not configured — password reset link for user %s: %s", user.id, link)
        if settings.is_dev:
            # Development convenience ONLY (APP_ENV=development/test). Never returned in production.
            return generic | {"dev_reset_link": link,
                              "dev_note": "SMTP is not configured; this link is shown only in development mode."}
    return generic


@router.post("/auth/reset-password")
def reset_password(body: ResetIn, request: Request, db: Session = Depends(get_db)):
    limiter.check(f"reset:{client_ip(request)}", 10, 3600)
    if body.password != body.confirm_password:
        raise HTTPException(422, "Passwords do not match.")
    if not password_ok(body.password):
        raise HTTPException(422, PASSWORD_RULE)
    pr = db.scalar(select(PasswordReset).where(PasswordReset.token_hash == sha256(body.token)))
    if not pr or pr.used or _as_aware(pr.expires_at) < datetime.now(timezone.utc):
        raise HTTPException(400, "This reset link is invalid or has expired. Please request a new one.")
    user = db.get(User, pr.user_id)
    user.password_hash = hash_password(body.password)
    pr.used = True
    revoke_all_sessions(db, user.id)
    db.commit()
    audit(db, "auth.password_reset", user.id, ip=client_ip(request))
    return {"message": "Your password has been reset. You can now log in."}


@router.patch("/me/profile")
def update_profile(body: ProfileIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user.full_name = " ".join(body.full_name.split())
    db.commit()
    return {"user": user_out(user)}


@router.post("/me/password")
def change_password(body: PasswordIn, request: Request, response: Response, user: User = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    limiter.check(f"pwchange:{user.id}", 5, 900)
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(400, "Your current password is incorrect.")
    if body.new_password != body.confirm_password:
        raise HTTPException(422, "Passwords do not match.")
    if not password_ok(body.new_password):
        raise HTTPException(422, PASSWORD_RULE)
    user.password_hash = hash_password(body.new_password)
    revoke_all_sessions(db, user.id)
    db.commit()
    create_session(db, user, response, request.headers.get("user-agent"))
    audit(db, "auth.password_changed", user.id, ip=client_ip(request))
    return {"message": "Password updated. Other devices have been signed out."}


@router.delete("/me/data")
def delete_my_data(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Delete all of the user's conversations and poems (keeps the account)."""
    n_conv = db.scalar(select(func.count(Conversation.id)).where(Conversation.user_id == user.id))
    db.execute(delete(Poem).where(Poem.user_id == user.id))
    db.execute(delete(Conversation).where(Conversation.user_id == user.id))
    db.commit()
    audit(db, "user.data_deleted", user.id, meta={"conversations": n_conv})
    return {"message": "All your conversations and poems have been deleted."}
