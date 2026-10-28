# AI-KEN — AI-Powered Emotional Story-to-Poem Generator Using RAG

**Your Story, Your Emotions, Your Poetry.**
AI-KEN turns personal stories into short, original poems in **Filipino, English, or Taglish**. Before writing, it retrieves poetry rules, literary techniques and dictionary vocabulary from its knowledge base (RAG), then validates the poem's structure — line counts, syllables, rhyme scheme, acrostic letters — and revises it when a check fails.

---

## 1. Features

| Area | What's implemented |
|---|---|
| **Accounts** | Registration (auto `user` role — the role field is ignored), login with password toggle, logout, forgot/reset password (email via SMTP; dev-mode link when SMTP isn't set), profile edit, change password, delete-my-data |
| **Security** | bcrypt hashing, server-side sessions in httpOnly SameSite cookies, CSRF header check, role checks on every admin route, rate limiting (login, register, reset, generation), CSP + security headers, input validation, parameterized SQL (SQLAlchemy), secrets only on the server |
| **Chat workspace** | ChatGPT-style UI, Enter to send / Shift+Enter newline, conversation history (search, rename, delete), suggested prompts, loading stages, responsive desktop/tablet/mobile |
| **Poems** | Regenerate, change structure, translate (Filipino ↔ English), copy, save, rename, delete, 1–5★ rating + comment, saved-poems collection |
| **Poem settings** | Language (auto/Filipino/English/Taglish), 19 forms, lines, syllable pattern, rhyme scheme, vocabulary level, emotional tone, vocabulary toggle, auto-choose structure, acrostic word — only relevant controls are shown per form |
| **Forms** | Haiku, Tanka, Acrostic, Sonnet (Shakespearean, Petrarchan), Limerick, Couplet, Quatrain, Free Verse, Ballad, Elegy, Ode, Diamante, Tanaga, Diona, Dalit, Awit, Korido, Custom |
| **RAG** | Knowledge documents + poetry forms + dictionary entries are chunked, embedded and stored as vectors; each poem retrieves rules, techniques and emotion-matched vocabulary before generation |
| **Validation** | Language-aware syllable counting (CMU Pronouncing Dictionary for English, vowel-based *pantig* for Filipino), rhyme detection (pronunciation for English, traditional *tugma* groups for Filipino), acrostic, words-per-line, stanzas, language consistency. Bounded revision loop; honest "estimate"/"Modern adaptation" labels |
| **Dictionary** | Curated Filipino/English emotional vocabulary with source + verification status, live English lookups (Free Dictionary API) cached with source, AI explanations clearly labeled *unverified*, Vocabulary of the Day |
| **Admin** | Dashboard (live stats, service health), user management (search/filter, activate/deactivate/suspend, roles, delete, create admins), knowledge base (upload .txt/.md/.csv/.pdf or paste, edit, delete, reprocess one/all, retrieval test, RAG logs), poetry form rules editor, dictionary CRUD + verification, analytics charts, system settings, audit logs |
| **Privacy** | Admin endpoints never return stories, messages or poem text; analytics are aggregate; audit and RAG logs never store passwords or story text |

---

## 2. Architecture

```
React (Vite, Tailwind, Recharts) ──/api──▶ FastAPI
                                           ├─ auth & sessions (bcrypt, httpOnly cookie)
                                           ├─ RAG pipeline  app/services/rag.py
                                           │   1 input → 2 clean → 3 language detection → 4 emotion analysis (LLM)
                                           │   → 5/6 vector retrieval (rules, techniques, dictionary)
                                           │   → 7 context augmentation → 8 generation (LLM)
                                           │   → 9 validation → 10 revision (≤ N attempts) → 11 response → 12 feedback
                                           ├─ vector store  (embeddings in kb_chunks, cosine search with NumPy)
                                           ├─ LLM provider  (Anthropic Claude or any OpenAI-compatible API)
                                           └─ SQL database  (SQLite dev / PostgreSQL or Supabase prod)
```

**Tech stack:** Python 3.11+ · FastAPI · SQLAlchemy 2 · NumPy · pronouncing (CMUdict) · pypdf · React 19 · Vite · Tailwind CSS 4 · Recharts · lucide-react.

---

## 3. Project structure

```
ai-ken/
├── backend/
│   ├── app/
│   │   ├── main.py              FastAPI app, startup seeding, security headers, serves frontend/dist
│   │   ├── config.py            environment configuration
│   │   ├── database.py, models.py
│   │   ├── security.py          hashing, sessions, role guards, CSRF, rate limiter
│   │   ├── cli.py               init / create-admin / reindex / export-schema
│   │   ├── routers/             auth.py · poems.py (user module) · admin.py
│   │   ├── services/
│   │   │   ├── rag.py           the 12-step pipeline
│   │   │   ├── llm.py           Anthropic / OpenAI-compatible providers (+ test-only mock)
│   │   │   ├── embeddings.py    local lexical or remote embeddings
│   │   │   ├── vectorstore.py   chunking + cosine retrieval
│   │   │   ├── knowledge.py     ingestion, seeding, reprocessing
│   │   │   ├── dictionary.py    lookups with provenance
│   │   │   ├── language.py      language detection + emotion lexicon
│   │   │   └── validation/      phonetics.py (syllables, rhyme) · validator.py
│   │   └── seed/                forms.py · dictionary.py · knowledge/*.md
│   ├── tests/                   43 pytest tests covering every required workflow
│   └── requirements.txt
├── frontend/                    React app (src/pages/app = user module, src/pages/admin = admin module)
├── tests-e2e/e2e_browser.py     Playwright browser walkthrough
├── docs/schema.sql              PostgreSQL DDL (generated from the models)
├── docs/DEPLOYMENT.md
├── Dockerfile, docker-compose.yml, .env.example
```

---

## 4. Installation (local)

**Requirements:** Python 3.11+ and Node.js 20.19+ or 22.12+ (Vite 8 needs it; older Node silently skips the native build binding).

### Windows (PowerShell)
```powershell
cd ai-ken\backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy ..\.env.example .env        # then edit .env (see §5)
uvicorn app.main:app --reload --port 8000
```
If `Activate.ps1` fails with *"running scripts is disabled on this system"*, either run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once, or skip activation and use `.\.venv\Scripts\python.exe -m pip …` / `.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000`.

In a second terminal:
```powershell
cd ai-ken\frontend
npm install
npm run dev
```

### macOS / Linux
```bash
cd ai-ken/backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example .env          # then edit .env
uvicorn app.main:app --reload --port 8000
# second terminal
cd ai-ken/frontend && npm install && npm run dev
```

Open **http://localhost:5173**. (Vite proxies `/api` to port 8000.)
On first start the backend creates the tables and seeds 19 poetry forms, 119 dictionary entries and 5 knowledge documents, then embeds them.

**Single-server mode:** run `npm run build` in `frontend/`; FastAPI then serves the built app at http://localhost:8000.

---

## 5. Configuration

Edit `backend/.env` (all options are documented in `.env.example`). The minimum to generate poems:

```ini
SECRET_KEY=<long random string>
ANTHROPIC_API_KEY=sk-ant-...           # from console.anthropic.com
ADMIN_EMAIL=you@example.com            # first admin, created at startup if none exists
ADMIN_PASSWORD=ChooseAStrong1
```

| Service | Needed? | How to configure |
|---|---|---|
| **Language model** | Yes, for generation, translation and AI explanations | `LLM_PROVIDER=anthropic` + `ANTHROPIC_API_KEY`. Or `LLM_PROVIDER=openai` + `OPENAI_API_KEY`/`OPENAI_BASE_URL`/`OPENAI_MODEL` for OpenAI, Groq, OpenRouter, Gemini's OpenAI endpoint, or a free local **Ollama** (`OPENAI_BASE_URL=http://localhost:11434/v1`). Without a key, the app runs and shows a clear "setup needed" message instead of pretending. |
| **Embeddings** | Works out of the box | Default `local` = offline lexical embeddings (no key). For semantic retrieval set `EMBEDDING_PROVIDER=openai` with an OpenAI, Voyage AI or Ollama embedding endpoint, then **Admin → AI & Knowledge Base → Reprocess all**. |
| **Database** | Works out of the box | SQLite file in `backend/data/`. For PostgreSQL/Supabase set `DATABASE_URL=postgresql://…`. |
| **English dictionary API** | Optional | Free Dictionary API, no key. Disable with `ENABLE_EXTERNAL_DICTIONARY=false`. |
| **Email** | Optional in development | `SMTP_*` settings for reset emails. In development without SMTP the reset link is shown on screen and logged to the console. |

### Creating administrators
Public registration **always** creates regular users. Admins are created by:
1. `ADMIN_EMAIL` / `ADMIN_PASSWORD` in `.env` (only when no admin exists yet), or
2. the CLI: `python -m app.cli create-admin --email you@example.com` (prompts for a password), or
3. an existing admin: **Admin → Users → New administrator** or **Make admin**.

---

## 6. Using AI-KEN

**User:** sign up → write your story → (optional) open **Poem Settings** → Enter. Each poem card shows detected emotions (an interpretation, not a diagnosis), the validation badge, and actions: Regenerate, Change structure, Translate, Vocabulary (with word lookup), Validation report, Save, Copy and rating. The sidebar holds history, saved poems, Vocabulary of the Day and profile.

**Admin:** log in with an admin account → dashboard. Upload reference documents (they're chunked and embedded immediately), test retrieval, edit form rules, review/verify dictionary entries, adjust limits and languages, and read audit logs.

---

## 7. Testing

```bash
cd backend
pip install -r requirements-dev.txt
python -m pytest -q          # 43 tests
```
The suite runs fully offline using a deterministic, **test-only** mock LLM (`APP_ENV=test`, `LLM_PROVIDER=mock` — impossible to select outside tests). It verifies, mapped to the specification's §16:

1 registration & duplicate emails · 2 login/logout/reset/protected routes · 3 automatic user role · 4 admin creation & role management · 5 role-based access · 6 story submission & generation · 7 Filipino/English output & language detection · 8 emotion interpretation & vocabulary · 9 RAG retrieval & context · 10 form selection, validation and the revision loop · 11 regenerate/save/translate/delete · 12 history & cross-user privacy · 13 KB upload/update/remove/reprocess · 14 dictionary attribution · 15 DB-backed analytics & audit logs (and that no story/poem text leaks to admins) · plus the "not configured" setup message.

**Browser test:** see the instructions at the top of `tests-e2e/e2e_browser.py` (Playwright). It registers, generates a tanaga, opens validation/vocabulary, saves, rates, translates, regenerates, checks Shift+Enter, logout protection, the reset flow, every admin page, a knowledge-base upload, user-blocked-from-admin, and mobile layouts.

**Manual check with a real model:** set `ANTHROPIC_API_KEY`, then try the Filipino tanaga example from the specification and confirm the validation report shows 7–7–7–7.

---

## 8. How validation stays honest

- **Filipino syllables (pantig):** every vowel letter = 1 syllable; *y/w* are consonants; *mga* = 2; apostrophe contractions reduce the count. English words inside Taglish lines use CMUdict.
- **Rhyme (tugma):** exact ending, or same vowel (e/i, o/u kin) + consonant in the same group — *malakas* b k d g p s t / *mahina* l m n ng r w y. Vowel-ending rhymes are reported as **estimates** because glottal stops aren't written.
- **English meter** for sonnets/limericks is approximated by syllable count and marked as an estimate.
- When a traditional form still fails after the allowed revisions, the poem is labeled **"Modern adaptation — did not fully satisfy the traditional … rules"**, never as a verified traditional poem.

---

## 9. Data model

Tables: `users`, `sessions`, `password_resets`, `conversations`, `messages`, `poems`, `feedback`, `knowledge_documents`, `kb_chunks` (vectors), `dictionary_entries`, `poetry_forms`, `audit_logs`, `rag_logs`, `system_settings`. Full PostgreSQL DDL: `docs/schema.sql` (regenerate with `python -m app.cli export-schema`). Tables are created automatically at startup; for long-term schema changes add Alembic migrations.

---

## 10. Limitations and next steps

- **Starter content needs review.** The seeded dictionary entries and knowledge documents were compiled for this project and are marked *pending review*. Before a defense or public launch, verify them against authoritative sources (KWF, UP Diksiyonaryong Filipino, Poetry Foundation, your literature references) and mark entries verified in the admin dashboard.
- **Local embeddings are lexical**, not semantic. Configure a remote embedding model for better retrieval of paraphrased ideas.
- **Rate limiting is in-memory**, per process. For multiple server instances use a shared store (e.g. Redis).
- Filipino syllable/rhyme rules cover native orthography well; Spanish/English loanwords spelled irregularly can be miscounted — those lines are flagged for manual review.

---

## 11. Troubleshooting

| Symptom | Fix |
|---|---|
| "AI generation isn't configured yet" | Add `ANTHROPIC_API_KEY` (or another provider) to `backend/.env` and restart. |
| "The AI service rejected the server's API key" | The key is wrong or revoked — check it in your provider console. |
| No admin account | `python -m app.cli create-admin --email you@example.com` |
| Retrieval quality is low after switching embeddings | Admin → AI & Knowledge Base → **Reprocess all**. |
| Reset emails don't arrive | Configure `SMTP_*`; in development the link appears on screen. |
| `SECRET_KEY must be set in production` | Set `SECRET_KEY` when `APP_ENV=production`. |

Deployment: see **[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)**.
