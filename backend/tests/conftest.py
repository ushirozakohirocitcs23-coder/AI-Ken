import os
import sys
import tempfile
from pathlib import Path

import pytest

_tmp = tempfile.mkdtemp(prefix="aiken-test-")
os.environ.update({
    "APP_ENV": "test",
    "LLM_PROVIDER": "mock",
    "EMBEDDING_PROVIDER": "local",
    "ENABLE_EXTERNAL_DICTIONARY": "false",
    "DATABASE_URL": f"sqlite:///{_tmp}/test.db",
    "ADMIN_EMAIL": "admin@example.org",
    "ADMIN_PASSWORD": "AdminPass123",
    "FRONTEND_DIST": f"{_tmp}/no-dist",
})
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.security import limiter  # noqa: E402

H = {"X-Requested-With": "AI-KEN"}


class Client(TestClient):
    def request(self, method, url, *a, **kw):
        headers = dict(kw.pop("headers", None) or {})
        if kw.pop("csrf", True):
            headers.setdefault("X-Requested-With", "AI-KEN")
        return super().request(method, url, *a, headers=headers, **kw)


@pytest.fixture(scope="session")
def app_started():
    with Client(app) as c:
        yield c


@pytest.fixture()
def client(app_started):
    limiter.reset()
    c = Client(app)
    yield c
    c.close()


_counter = {"n": 0}


@pytest.fixture()
def user_client(client):
    _counter["n"] += 1
    email = f"user{_counter['n']}@example.com"
    r = client.post("/api/auth/register", json={"full_name": "Juan Dela Cruz", "email": email,
                                                 "password": "Secret123", "confirm_password": "Secret123"})
    assert r.status_code == 201, r.text
    client.email = email
    return client


@pytest.fixture()
def admin_client(app_started):
    limiter.reset()
    c = Client(app)
    r = c.post("/api/auth/login", json={"email": "admin@example.org", "password": "AdminPass123"})
    assert r.status_code == 200, r.text
    yield c
    c.close()
