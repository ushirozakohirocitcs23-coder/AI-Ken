"""Workflows 1-5: registration, duplicate prevention, login/logout, password recovery, protected
routes, automatic user role, secure admin creation and role-based access."""


def reg(client, email, **kw):
    body = {"full_name": "Maria Santos", "email": email, "password": "Secret123", "confirm_password": "Secret123"}
    body.update(kw)
    return client.post("/api/auth/register", json=body)


def test_register_assigns_user_role_and_ignores_role_field(client):
    r = reg(client, "maria@example.com", role="admin")
    assert r.status_code == 201
    assert r.json()["user"]["role"] == "user"
    assert client.get("/api/auth/me").json()["user"]["role"] == "user"
    assert client.get("/api/admin/overview").status_code == 403


def test_duplicate_email_rejected_case_insensitive(client):
    assert reg(client, "dupe@example.com").status_code == 201
    r = reg(client, "DUPE@example.com")
    assert r.status_code == 409
    assert "already exists" in r.json()["detail"]


def test_register_validation(client):
    assert reg(client, "a@example.com", confirm_password="Other1234").status_code == 422
    assert reg(client, "b@example.com", password="short", confirm_password="short").status_code == 422
    assert reg(client, "c@example.com", password="allletters", confirm_password="allletters").status_code == 422
    assert reg(client, "not-an-email").status_code == 422
    assert reg(client, "d@example.com", full_name=" ").status_code == 422


def test_login_logout_and_protected_routes(client):
    reg(client, "login@example.com")
    client.post("/api/auth/logout")
    assert client.get("/api/auth/me").status_code == 401
    assert client.get("/api/conversations").status_code == 401
    bad = client.post("/api/auth/login", json={"email": "login@example.com", "password": "Wrong1234"})
    assert bad.status_code == 401
    ok = client.post("/api/auth/login", json={"email": "login@example.com", "password": "Secret123"})
    assert ok.status_code == 200 and ok.json()["redirect"] == "/app"
    assert client.get("/api/conversations").status_code == 200
    # session cookie is httponly
    assert "httponly" in ok.headers["set-cookie"].lower()
    client.post("/api/auth/logout")
    assert client.get("/api/conversations").status_code == 401


def test_logout_invalidates_server_session_even_if_cookie_replayed(client):
    reg(client, "replay@example.com")
    token = client.cookies.get("aiken_session")
    client.post("/api/auth/logout")
    client.cookies.set("aiken_session", token)
    assert client.get("/api/auth/me").status_code == 401


def test_csrf_header_required(client):
    r = client.request("POST", "/api/auth/login", json={"email": "x@example.com", "password": "Secret123"}, csrf=False)
    assert r.status_code == 403


def test_password_reset_flow(client):
    reg(client, "reset@example.com")
    client.post("/api/auth/logout")
    r = client.post("/api/auth/forgot-password", json={"email": "reset@example.com"})
    assert r.status_code == 200
    link = r.json()["dev_reset_link"]
    token = link.split("token=")[1]
    # unknown email gives the same generic answer (no account enumeration)
    r2 = client.post("/api/auth/forgot-password", json={"email": "nobody@example.com"})
    assert r2.json()["message"] == r.json()["message"] and "dev_reset_link" not in r2.json()
    assert client.post("/api/auth/reset-password", json={"token": token, "password": "NewSecret9",
                                                          "confirm_password": "NewSecret9"}).status_code == 200
    # token is single-use
    assert client.post("/api/auth/reset-password", json={"token": token, "password": "NewSecret9",
                                                          "confirm_password": "NewSecret9"}).status_code == 400
    assert client.post("/api/auth/login", json={"email": "reset@example.com", "password": "Secret123"}).status_code == 401
    assert client.post("/api/auth/login", json={"email": "reset@example.com", "password": "NewSecret9"}).status_code == 200


def test_change_password_and_profile(user_client):
    r = user_client.patch("/api/me/profile", json={"full_name": "Juan  P.  Dela Cruz"})
    assert r.json()["user"]["full_name"] == "Juan P. Dela Cruz"
    assert user_client.post("/api/me/password", json={"current_password": "nope", "new_password": "Another123",
                                                      "confirm_password": "Another123"}).status_code == 400
    assert user_client.post("/api/me/password", json={"current_password": "Secret123", "new_password": "Another123",
                                                      "confirm_password": "Another123"}).status_code == 200
    assert user_client.get("/api/auth/me").status_code == 200  # current device stays signed in


def test_admin_login_redirect_and_access(admin_client):
    me = admin_client.get("/api/auth/me").json()["user"]
    assert me["role"] == "admin"
    assert admin_client.get("/api/admin/overview").status_code == 200


def test_admin_creates_admin_and_manages_roles(admin_client, client):
    r = admin_client.post("/api/admin/users/admins", json={"full_name": "Second Admin", "email": "admin2@example.org",
                                                           "password": "AdminTwo123"})
    assert r.status_code == 201 and r.json()["user"]["role"] == "admin"
    reg(client, "promote@example.com")
    uid = client.get("/api/auth/me").json()["user"]["id"]
    assert admin_client.patch(f"/api/admin/users/{uid}", json={"role": "admin"}).json()["user"]["role"] == "admin"
    assert client.get("/api/admin/overview").status_code == 200
    admin_client.patch(f"/api/admin/users/{uid}", json={"role": "user"})
    assert client.get("/api/admin/overview").status_code == 403


def test_suspended_user_is_logged_out_and_blocked(admin_client, client):
    reg(client, "suspend@example.com")
    uid = client.get("/api/auth/me").json()["user"]["id"]
    admin_client.patch(f"/api/admin/users/{uid}", json={"status": "suspended"})
    assert client.get("/api/auth/me").status_code in (401, 403)
    r = client.post("/api/auth/login", json={"email": "suspend@example.com", "password": "Secret123"})
    assert r.status_code == 403 and "suspended" in r.json()["detail"]


def test_admin_cannot_demote_self(admin_client):
    me = admin_client.get("/api/auth/me").json()["user"]
    assert admin_client.patch(f"/api/admin/users/{me['id']}", json={"role": "user"}).status_code == 400


def test_login_rate_limited(client):
    for _ in range(8):
        client.post("/api/auth/login", json={"email": "brute@example.com", "password": "Wrong1234"})
    r = client.post("/api/auth/login", json={"email": "brute@example.com", "password": "Wrong1234"})
    assert r.status_code == 429
