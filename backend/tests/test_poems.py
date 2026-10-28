"""Workflows 6-12: story submission, generation in Filipino/English, emotion interpretation,
vocabulary retrieval, RAG context, validation + revision, regenerate/copy/save/translate/delete,
conversation history and privacy."""
from app.services import llm

EN_STORY = ("I always try my best to make everyone happy, but sometimes I feel like nobody notices my efforts. "
            "I smile in front of everyone, even when I feel tired inside.")
FIL_STORY = ("Masaya ako kapag kasama ko ang pamilya ko, pero minsan nalulungkot ako kapag iniisip ko ang mga "
             "pangarap na hindi ko pa naaabot.")


def gen(c, story=EN_STORY, **settings):
    return c.post("/api/generate", json={"story": story, "settings": settings})


def poem_of(resp):
    return resp.json()["messages"][1]["poem"]


def test_english_generation_with_rag_and_validation(user_client):
    r = gen(user_client, poem_type="quatrain", rhyme_scheme="AABB", language="en")
    assert r.status_code == 200, r.text
    p = poem_of(r)
    assert p["language"] == "en" and p["poem_type"] == "quatrain"
    assert p["content"].count("\n") == 3
    assert p["validation"]["overall"] == "pass"
    assert {c["name"] for c in p["validation"]["checks"]} >= {"Line count", "Rhyme scheme"}
    emos = {e["emotion"] for e in p["detected_emotions"]}
    assert "sadness" in emos
    # RAG: knowledge chunks and dictionary candidates were retrieved and recorded
    assert p["retrieval"]["documents"], "expected knowledge-base documents in context"
    assert p["retrieval"]["vocabulary_candidates"]
    # vocabulary: dictionary entry for a word the poem uses, with provenance
    vocab = {v["word"]: v for v in p["vocabulary"]}
    assert "unseen" in vocab and vocab["unseen"]["provenance"] in {"curated_unreviewed", "verified"}


def test_filipino_tanaga_revision_loop(user_client):
    r = gen(user_client, story=FIL_STORY, poem_type="tanaga", language="fil", vocabulary_level="intermediate")
    assert r.status_code == 200, r.text
    p = poem_of(r)
    v = p["validation"]
    assert p["language"] == "fil" and p["poem_type"] == "tanaga"
    assert v["revision_attempts"] == 1          # mock's first draft has 8-syllable lines → revised
    assert v["overall"] in {"pass", "pass_estimate"}
    assert all(l["syllables"] == 7 for l in v["lines"])
    assert "ligaya" in {x["word"] for x in p["vocabulary"]}


def test_auto_language_and_form(user_client):
    p = poem_of(gen(user_client, story=FIL_STORY))
    assert p["analysis"]["input_language"]["language"] == "fil"
    assert p["language"] == "fil" and p["poem_type"] == "tanaga"
    assert any("chose" in n for n in p["validation"]["notes"])


def test_haiku_and_acrostic(user_client):
    h = poem_of(gen(user_client, poem_type="haiku", language="en"))
    assert h["validation"]["overall"] == "pass"
    syl = next(c for c in h["validation"]["checks"] if c["name"] == "Syllable pattern")
    assert syl["actual"] == "5–7–5"
    a = poem_of(gen(user_client, poem_type="acrostic", acrostic_word="love", language="en"))
    ac = next(c for c in a["validation"]["checks"] if c["name"] == "Acrostic")
    assert ac["status"] == "pass" and ac["actual"] == "LOVE"


def test_locked_traditional_structure_not_overridden(user_client):
    p = poem_of(gen(user_client, poem_type="haiku", lines=7, language="en"))
    assert p["settings"]["effective_rules"]["lines"] == 3
    assert any("requires 3 lines" in n for n in p["validation"]["notes"])


def test_failed_structure_is_labeled_not_claimed(user_client, monkeypatch):
    from app.services import llm_mock
    monkeypatch.setattr(llm_mock, "TANAGA_OK", llm_mock.TANAGA_BAD)  # revisions never fix it
    p = poem_of(gen(user_client, story=FIL_STORY, poem_type="tanaga", language="fil"))
    assert p["validation"]["overall"] == "fail"
    assert "Modern adaptation" in p["validation"]["status_label"]


def test_regenerate_save_rename_translate_delete(user_client):
    r = gen(user_client, poem_type="quatrain", language="en")
    conv_id = r.json()["conversation"]["id"]
    pid = poem_of(r)["id"]
    rg = user_client.post(f"/api/poems/{pid}/regenerate", json={})
    assert rg.status_code == 200
    new = rg.json()["message"]["poem"]
    assert new["kind"] == "regeneration" and new["poem_type"] == "quatrain"
    # change structure on regenerate
    alt = user_client.post(f"/api/poems/{pid}/regenerate", json={"settings": {"poem_type": "haiku", "language": "en"}})
    assert alt.json()["message"]["poem"]["poem_type"] == "haiku"
    # save + rename
    assert user_client.patch(f"/api/poems/{pid}", json={"is_saved": True, "title": "My Smile"}).json()["poem"]["is_saved"]
    saved = user_client.get("/api/poems?saved=true").json()["poems"]
    assert [p["title"] for p in saved] == ["My Smile"]
    # translate to Filipino
    tr = user_client.post(f"/api/poems/{pid}/translate", json={"target": "fil"})
    assert tr.status_code == 200, tr.text
    tp = tr.json()["message"]["poem"]
    assert tp["language"] == "fil" and tp["kind"] == "translation" and tp["parent_poem_id"] == pid
    # history contains everything in order
    conv = user_client.get(f"/api/conversations/{conv_id}").json()
    assert [m["sender"] for m in conv["messages"]] == ["user", "assistant", "assistant", "assistant", "assistant"]
    # feedback
    fb = user_client.post(f"/api/poems/{pid}/feedback", json={"rating": 5, "comments": "Ang ganda!"})
    assert fb.status_code == 200
    assert user_client.get(f"/api/poems/{pid}").json()["poem"]["feedback"]["rating"] == 5
    # delete poem, then conversation
    assert user_client.delete(f"/api/poems/{pid}").status_code == 200
    assert user_client.get(f"/api/poems/{pid}").status_code == 404
    assert user_client.delete(f"/api/conversations/{conv_id}").status_code == 200
    assert user_client.get(f"/api/conversations/{conv_id}").status_code == 404


def test_users_cannot_access_each_others_data(client):
    client.post("/api/auth/register", json={"full_name": "Owner", "email": "owner@example.com",
                                            "password": "Secret123", "confirm_password": "Secret123"})
    r = gen(client, poem_type="quatrain", language="en")
    pid, cid = poem_of(r)["id"], r.json()["conversation"]["id"]
    client.post("/api/auth/logout")
    client.post("/api/auth/register", json={"full_name": "Intruder", "email": "intruder@example.com",
                                            "password": "Secret123", "confirm_password": "Secret123"})
    assert client.get(f"/api/poems/{pid}").status_code == 404
    assert client.get(f"/api/conversations/{cid}").status_code == 404
    assert client.delete(f"/api/poems/{pid}").status_code == 404
    assert client.post(f"/api/poems/{pid}/regenerate", json={}).status_code == 404
    assert client.post("/api/generate", json={"story": "hi", "conversation_id": cid}).status_code == 404
    assert client.get("/api/conversations").json()["conversations"] == []


def test_llm_not_configured_returns_setup_message(user_client, monkeypatch):
    monkeypatch.setattr(llm.settings, "llm_provider", "anthropic")
    monkeypatch.setattr(llm.settings, "anthropic_api_key", "")
    r = gen(user_client)
    assert r.status_code == 503
    assert r.json()["detail"]["code"] == "llm_not_configured"
    assert "ANTHROPIC_API_KEY" in r.json()["detail"]["setup_hint"]
    assert user_client.get("/api/conversations").json()["conversations"] == []  # nothing pretended/stored


def test_story_validation_and_wellbeing_note(user_client):
    assert gen(user_client, story="   ").status_code in (400, 422)
    p = poem_of(gen(user_client, story="I feel like I want to hurt myself, nobody notices me.", poem_type="free_verse",
                    language="en"))
    assert p["analysis"]["support_note"] and "1553" in p["analysis"]["support_note"]


def test_dictionary_lookup_and_word_of_day(user_client):
    e = user_client.get("/api/dictionary/lookup", params={"word": "Pag-asa", "language": "fil"}).json()["entry"]
    assert e["definition"].startswith("Paniniwalang") and e["verified"] is False and e["source"]
    miss = user_client.get("/api/dictionary/lookup", params={"word": "zzzqword"}).json()
    assert miss["entry"] is None
    ai = user_client.get("/api/dictionary/lookup", params={"word": "zzzqword", "ai": True}).json()["entry"]
    assert ai["provenance"] == "ai_generated" and "not verified" in ai["source"]
    assert user_client.get("/api/dictionary/word-of-the-day").json()["entry"]["word"]


def test_forms_endpoint_and_daily_limit(user_client, admin_client):
    forms = user_client.get("/api/forms").json()["forms"]
    keys = {f["key"] for f in forms}
    assert {"haiku", "tanaga", "diona", "sonnet_shakespearean", "diamante", "awit", "korido"} <= keys
    admin_client.put("/api/admin/settings", json={"values": {"daily_generation_limit": 1}})
    try:
        assert gen(user_client, poem_type="haiku", language="en").status_code == 200
        assert gen(user_client, poem_type="haiku", language="en").status_code == 429
    finally:
        admin_client.put("/api/admin/settings", json={"values": {"daily_generation_limit": 50}})


def test_delete_all_my_data(user_client):
    gen(user_client, poem_type="haiku", language="en")
    assert user_client.delete("/api/me/data").status_code == 200
    assert user_client.get("/api/conversations").json()["conversations"] == []
    assert user_client.get("/api/poems?saved=false").json()["poems"] == []
