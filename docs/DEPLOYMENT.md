# Deploying AI-KEN

AI-KEN deploys as **one web service**: FastAPI serves both the API (`/api/*`) and the built React app, so cookies stay same-origin and no CORS setup is needed.

## Production checklist
- [ ] `APP_ENV=production` (disables dev reset links and `/api/docs`)
- [ ] `SECRET_KEY` — long random value (`python -c "import secrets; print(secrets.token_urlsafe(48))"`)
- [ ] `COOKIE_SECURE=true` (HTTPS only)
- [ ] `PUBLIC_URL=https://your-domain` (used in reset emails)
- [ ] `DATABASE_URL` → PostgreSQL / Supabase (not SQLite) for durable data
- [ ] `ANTHROPIC_API_KEY` (or another LLM provider)
- [ ] `SMTP_*` for password-reset emails
- [ ] `ADMIN_EMAIL` / `ADMIN_PASSWORD` for the first admin (remove from env afterwards if you like)
- [ ] Optional: remote embeddings (`EMBEDDING_PROVIDER=openai`) then **Reprocess all**
- [ ] Review and verify the starter dictionary and knowledge documents

## Option A — Docker (any VPS, Railway, Fly.io, Render)
```bash
cp .env.example .env     # fill in production values
docker build -t ai-ken .
docker run -p 8000:8000 --env-file .env ai-ken
```
Or with the bundled PostgreSQL: `docker compose up --build -d` → http://localhost:8000.
The container listens on `$PORT` (default 8000) and runs as a non-root user.

## Option B — Render.com (free tier friendly)
1. Push the project to GitHub.
2. Create a **PostgreSQL** instance on Render (or use Supabase) and copy its connection string.
3. New → **Web Service** → your repo → *Runtime: Docker* (uses the root `Dockerfile`).
4. Environment: add the variables from the checklist, with `DATABASE_URL` from step 2.
5. Deploy. Render provides HTTPS; keep `COOKIE_SECURE=true`.

## Option C — Supabase as the database
In Supabase → Project Settings → Database, copy the **connection string (URI)** and set
`DATABASE_URL=postgresql://postgres.<ref>:<password>@<host>:5432/postgres`.
Tables are created automatically on first start (or run `docs/schema.sql` in the SQL editor).
AI-KEN uses its own secure session auth, so Supabase Auth is not required.

## Option D — Without Docker (Ubuntu VPS)
```bash
sudo apt install python3-venv nodejs npm nginx
git clone <repo> /opt/ai-ken && cd /opt/ai-ken
(cd frontend && npm ci && npm run build)
cd backend && python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt
cp ../.env.example .env   # edit
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --proxy-headers --workers 2
```
Run uvicorn under systemd and put Nginx in front with TLS (Let's Encrypt):
```nginx
server {
  server_name your-domain;
  client_max_body_size 12m;            # knowledge-base uploads up to 10 MB
  location / { proxy_pass http://127.0.0.1:8000; proxy_set_header Host $host;
               proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
               proxy_set_header X-Forwarded-Proto $scheme; proxy_read_timeout 180s; }
}
```
`proxy_read_timeout` matters: a poem with revisions can take 20–60 seconds.

## Operations
- **Backups:** back up the PostgreSQL database (stories, poems, accounts, knowledge base).
- **Re-indexing:** after changing embedding provider/model run `python -m app.cli reindex` or use the admin button.
- **Admins:** `python -m app.cli create-admin --email ...` inside the container/VM.
- **Logs:** application logs go to stdout; security events are in Admin → Security & Audit Logs.
- **Scaling:** the in-memory rate limiter and vector cache are per process. With several instances, move rate limiting to Redis and consider pgvector for the vector store (`app/services/vectorstore.py` keeps the same `add_chunks`/`search` interface).
