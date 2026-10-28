"""Workflows 13-15: knowledge-base upload/update/removal/reprocessing, dictionary attribution,
database-backed analytics and audit logs, and admin privacy boundaries."""
import io
import json

from .test_poems import EN_STORY, gen


def test_kb_upload_search_update_reprocess_delete(admin_client):
    text = ("# Kundiman\nAng kundiman ay awit ng pag-ibig na madalas malungkot at puno ng pangungulila. "
            "Gamitin ang larawang-diwa ng buwan at harana.")
    r = admin_client.post("/api/admin/knowledge", data={"title": "Kundiman notes", "language": "fil",
                                                         "doc_type": "reference", "source": "Class notes"},
                          files={"file": ("kundiman.md", io.BytesIO(text.encode()), "text/markdown")})
    assert r.status_code == 201, r.text
    doc = r.json()["document"]
    assert doc["status"] == "ready" and doc["chunk_count"] >= 1
    hits = admin_client.post("/api/admin/knowledge/search-test",
                             json={"query": "kundiman harana buwan", "source_type": "document"}).json()["hits"]
    assert hits and hits[0]["source_id"] == doc["id"]
    up = admin_client.patch(f"/api/admin/knowledge/{doc['id']}", json={"content": text + "\nIdagdag: tinig ng gitara."})
    assert up.json()["document"]["status"] == "ready"
    assert admin_client.post(f"/api/admin/knowledge/{doc['id']}/reprocess").json()["document"]["status"] == "ready"
    assert admin_client.delete(f"/api/admin/knowledge/{doc['id']}").status_code == 200
    hits = admin_client.post("/api/admin/knowledge/search-test",
                             json={"query": "kundiman harana buwan", "source_type": "document"}).json()["hits"]
    assert all(h["source_id"] != doc["id"] for h in hits)


def test_kb_rejects_bad_files(admin_client):
    r = admin_client.post("/api/admin/knowledge", data={"title": "x"},
                          files={"file": ("x.exe", io.BytesIO(b"MZ"), "application/octet-stream")})
    assert r.status_code == 415


def test_reprocess_all(admin_client):
    r = admin_client.post("/api/admin/knowledge/reprocess-all").json()
    assert r["result"]["documents"] >= 5 and r["result"]["forms"] >= 19 and r["stats"]["stale_chunks"] == 0


def test_dictionary_crud_with_source_attribution(admin_client, user_client):
    body = {"word": "Harana", "language": "fil", "part_of_speech": "pangngalan",
            "definition": "Pag-awit sa ilalim ng bintana ng nililigawan.", "synonyms": ["serenata"],
            "emotion_category": "love", "source": "UP Diksiyonaryong Filipino (checked)", "verified": True}
    r = admin_client.post("/api/admin/dictionary", json=body)
    assert r.status_code == 201
    eid = r.json()["entry"]["id"]
    assert admin_client.post("/api/admin/dictionary", json=body).status_code == 409
    e = user_client.get("/api/dictionary/lookup", params={"word": "harana"}).json()["entry"]
    assert e["verified"] and e["source"].startswith("UP") and e["provenance"] == "verified"
    body["verified"] = False
    assert admin_client.put(f"/api/admin/dictionary/{eid}", json=body).json()["entry"]["verified"] is False
    assert admin_client.post("/api/admin/dictionary", json=body | {"word": "x", "source": ""}).status_code == 422
    assert admin_client.delete(f"/api/admin/dictionary/{eid}").status_code == 200


def test_analytics_and_overview_are_db_backed_and_private(admin_client, user_client):
    before = admin_client.get("/api/admin/overview").json()["poems"]["total"]
    r = gen(user_client, poem_type="quatrain", language="en")
    pid = r.json()["messages"][1]["poem"]["id"]
    user_client.post(f"/api/poems/{pid}/feedback", json={"rating": 4})
    ov = admin_client.get("/api/admin/overview").json()
    assert ov["poems"]["total"] == before + 1
    assert ov["feedback"]["count"] >= 1
    an = admin_client.get("/api/admin/analytics?days=30").json()
    assert sum(d["poems"] for d in an["poems_by_date"]) >= 1
    assert any(f["key"] == "quatrain" for f in an["forms"])
    assert an["ratings"]["count"] >= 1
    # privacy: no admin payload contains story or poem text
    blob = json.dumps([ov, an, admin_client.get("/api/admin/users").json(),
                       admin_client.get("/api/admin/audit-logs").json(), admin_client.get("/api/admin/rag-logs").json()])
    assert "nobody notices" not in blob and EN_STORY[:30] not in blob
    assert "I wear a smile" not in blob


def test_audit_logs_record_security_events(admin_client, client):
    client.post("/api/auth/login", json={"email": "nobody@example.com", "password": "Wrong1234"})
    admin_client.put("/api/admin/settings", json={"values": {"retrieval_top_k": 6}})
    actions = {l["action"] for l in admin_client.get("/api/admin/audit-logs?per_page=200").json()["logs"]}
    assert {"auth.login_failed", "admin.settings_updated", "auth.login"} <= actions
    blob = json.dumps(admin_client.get("/api/admin/audit-logs?per_page=200").json())
    assert "Wrong1234" not in blob and "Secret123" not in blob


def test_settings_validation_and_language_toggle(admin_client, user_client):
    assert admin_client.put("/api/admin/settings", json={"values": {"bogus": 1}}).status_code == 422
    assert admin_client.put("/api/admin/settings", json={"values": {"max_revision_attempts": 9}}).status_code == 422
    admin_client.put("/api/admin/settings", json={"values": {"enabled_languages": ["en"]}})
    try:
        r = gen(user_client, language="fil", poem_type="free_verse")
        assert r.status_code == 400 and "disabled" in r.json()["detail"]
    finally:
        admin_client.put("/api/admin/settings", json={"values": {"enabled_languages": ["fil", "en", "taglish"]}})


def test_form_management(admin_client, user_client):
    forms = admin_client.get("/api/admin/forms").json()["forms"]
    diona = next(f for f in forms if f["key"] == "diona")
    admin_client.patch(f"/api/admin/forms/{diona['id']}", json={"enabled": False})
    assert "diona" not in {f["key"] for f in user_client.get("/api/forms").json()["forms"]}
    admin_client.patch(f"/api/admin/forms/{diona['id']}", json={"enabled": True})
    assert admin_client.patch(f"/api/admin/forms/{diona['id']}", json={"rules": {"evil": 1}}).status_code == 422


def test_health_reports_services(admin_client):
    h = admin_client.get("/api/admin/health").json()
    assert h["ai"]["provider"] == "mock" and h["vector_store"]["ok"]
    assert h["embeddings"]["model"].startswith("local-hash")
