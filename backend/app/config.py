"""Application configuration loaded from environment variables.

All secrets (API keys, session secret, SMTP credentials) live ONLY on the server
and are read from the environment / a local `.env` file. Nothing here is ever
sent to the browser.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _load_dotenv(path: Path) -> None:
    """Minimal .env loader (no extra dependency). Existing env vars win."""
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip('"').strip("'")
        if value:  # blank entries (e.g. `DATABASE_URL=`) mean "use the default"
            os.environ.setdefault(key, value)


_load_dotenv(BASE_DIR / ".env")
_load_dotenv(BASE_DIR.parent / ".env")


def _bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


@dataclass
class Settings:
    app_env: str = field(default_factory=lambda: os.getenv("APP_ENV", "development"))
    app_name: str = "AI-KEN"
    public_url: str = field(default_factory=lambda: os.getenv("PUBLIC_URL", "http://localhost:8000"))
    database_url: str = field(
        default_factory=lambda: os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'data' / 'aiken.db'}")
    )
    secret_key: str = field(default_factory=lambda: os.getenv("SECRET_KEY", ""))
    session_days: int = field(default_factory=lambda: int(os.getenv("SESSION_DAYS", "7")))
    cookie_secure: bool = field(default_factory=lambda: _bool("COOKIE_SECURE", False))
    cors_origins: list[str] = field(
        default_factory=lambda: [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if o.strip()]
    )

    # LLM
    llm_provider: str = field(default_factory=lambda: os.getenv("LLM_PROVIDER", "anthropic").lower())
    anthropic_api_key: str = field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY", ""))
    anthropic_model: str = field(default_factory=lambda: os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5-5"))
    openai_api_key: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    openai_base_url: str = field(default_factory=lambda: os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"))
    openai_model: str = field(default_factory=lambda: os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
    llm_timeout: float = field(default_factory=lambda: float(os.getenv("LLM_TIMEOUT", "90")))

    # Embeddings
    embedding_provider: str = field(default_factory=lambda: os.getenv("EMBEDDING_PROVIDER", "local").lower())
    embedding_api_key: str = field(default_factory=lambda: os.getenv("EMBEDDING_API_KEY", ""))
    embedding_base_url: str = field(default_factory=lambda: os.getenv("EMBEDDING_BASE_URL", "https://api.openai.com/v1"))
    embedding_model: str = field(default_factory=lambda: os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"))

    # Dictionary
    english_dictionary_api: str = field(
        default_factory=lambda: os.getenv("ENGLISH_DICTIONARY_API", "https://api.dictionaryapi.dev/api/v2/entries/en/")
    )
    enable_external_dictionary: bool = field(default_factory=lambda: _bool("ENABLE_EXTERNAL_DICTIONARY", True))

    # Email (password reset)
    smtp_host: str = field(default_factory=lambda: os.getenv("SMTP_HOST", ""))
    smtp_port: int = field(default_factory=lambda: int(os.getenv("SMTP_PORT", "587")))
    smtp_user: str = field(default_factory=lambda: os.getenv("SMTP_USER", ""))
    smtp_password: str = field(default_factory=lambda: os.getenv("SMTP_PASSWORD", ""))
    smtp_from: str = field(default_factory=lambda: os.getenv("SMTP_FROM", "AI-KEN <no-reply@ai-ken.local>"))

    # Bootstrap admin (only used if no admin exists yet)
    bootstrap_admin_email: str = field(default_factory=lambda: os.getenv("ADMIN_EMAIL", ""))
    bootstrap_admin_password: str = field(default_factory=lambda: os.getenv("ADMIN_PASSWORD", ""))
    bootstrap_admin_name: str = field(default_factory=lambda: os.getenv("ADMIN_NAME", "AI-KEN Administrator"))

    upload_dir: Path = field(default_factory=lambda: Path(os.getenv("UPLOAD_DIR", str(BASE_DIR / "data" / "uploads"))))
    frontend_dist: Path = field(
        default_factory=lambda: Path(os.getenv("FRONTEND_DIST", str(BASE_DIR.parent / "frontend" / "dist")))
    )

    @property
    def is_dev(self) -> bool:
        return self.app_env in {"development", "dev", "test"}

    @property
    def is_test(self) -> bool:
        return self.app_env == "test"

    def effective_secret(self) -> str:
        if self.secret_key:
            return self.secret_key
        if self.is_dev:
            return "dev-only-insecure-secret-change-me"
        raise RuntimeError("SECRET_KEY must be set in production.")

    def llm_configured(self) -> tuple[bool, str]:
        p = self.llm_provider
        if p == "anthropic":
            return (bool(self.anthropic_api_key), "Set ANTHROPIC_API_KEY in backend/.env (get one at console.anthropic.com).")
        if p == "openai":
            return (bool(self.openai_api_key) or "localhost" in self.openai_base_url or "127.0.0.1" in self.openai_base_url,
                    "Set OPENAI_API_KEY (and OPENAI_BASE_URL for compatible providers) in backend/.env.")
        if p == "mock":
            return (self.is_test, "The mock LLM provider is only available when APP_ENV=test.")
        return (False, f"Unknown LLM_PROVIDER '{p}'. Use 'anthropic' or 'openai'.")


settings = Settings()
