from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import delete, func, select

from .config import settings
from .database import Base, SessionLocal, engine
from .models import User, UserSession
from .routers import admin, auth, poems
from .security import csrf_guard, hash_password, password_ok
from .services.audit import audit
from .services.knowledge import ensure_index_current, seed

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("aiken")


def bootstrap(db) -> None:
    Base.metadata.create_all(engine)
    created = seed(db)
    if any(created.values()):
        log.info("Seeded knowledge base: %s", created)
    ensure_index_current(db)
    db.execute(delete(UserSession).where(UserSession.expires_at < datetime.now(timezone.utc)))
    db.commit()
    has_admin = db.scalar(select(func.count(User.id)).where(User.role == "admin"))
    if not has_admin and settings.bootstrap_admin_email and settings.bootstrap_admin_password:
        if not password_ok(settings.bootstrap_admin_password):
            log.error("ADMIN_PASSWORD does not meet the password policy; bootstrap admin not created.")
            return
        email = settings.bootstrap_admin_email.lower().strip()
        existing = db.scalar(select(User).where(func.lower(User.email) == email))
        if existing:
            existing.role = "admin"
        else:
            existing = User(full_name=settings.bootstrap_admin_name, email=email,
                            password_hash=hash_password(settings.bootstrap_admin_password), role="admin")
            db.add(existing)
        db.commit()
        audit(db, "system.bootstrap_admin", None, f"user:{existing.id}", {"email": email})
        log.info("Bootstrap administrator ready: %s", email)
    elif not has_admin:
        log.warning("No administrator exists. Create one with: python -m app.cli create-admin")


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings.effective_secret()  # fail fast in production without SECRET_KEY
    with SessionLocal() as db:
        bootstrap(db)
    yield


app = FastAPI(title="AI-KEN API", version="1.0.0", lifespan=lifespan, dependencies=[Depends(csrf_guard)],
              docs_url="/api/docs" if settings.is_dev else None, redoc_url=None, openapi_url="/api/openapi.json" if settings.is_dev else None)

app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_credentials=True,
                   allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
                   allow_headers=["content-type", "x-requested-with"])


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    if not request.url.path.startswith("/api/docs"):
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; script-src 'self'; connect-src 'self'; frame-ancestors 'none'")
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    return response


app.include_router(auth.router)
app.include_router(poems.router)
app.include_router(admin.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception):
    log.exception("Unhandled error on %s", request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Something went wrong on our side. Please try again."})


# ---------- serve the built React app (single-origin deployment) ----------
dist = settings.frontend_dist
if (dist / "index.html").exists():
    if (dist / "assets").exists():
        app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa(full_path: str):
        if full_path.startswith("api/"):
            return JSONResponse(status_code=404, content={"detail": "Not found"})
        candidate = (dist / full_path).resolve()
        if full_path and candidate.is_file() and dist.resolve() in candidate.parents:
            return FileResponse(candidate)
        return FileResponse(dist / "index.html")
else:
    @app.get("/", include_in_schema=False)
    def no_frontend():
        return HTMLResponse("<h1>AI-KEN API is running</h1><p>The frontend has not been built yet. Run "
                            "<code>npm run build</code> in <code>frontend/</code>, or use the Vite dev server on port 5173.</p>")
