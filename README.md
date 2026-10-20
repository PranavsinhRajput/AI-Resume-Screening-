# Resume Screening AI

Upload PDF resumes into a private library and search them in plain language ("Python developers who have deployed ML models to production"). Each resume is parsed into structured data and embeddings, and every search combines exact SQL filters, pgvector semantic search, and Gemini verification. Results come back ranked, with explanations and evidence.

- **Frontend:** React (JavaScript) + Vite + Tailwind v4 → Vercel
- **Backend:** FastAPI (Python 3.12) + PyMuPDF + fastembed (`BAAI/bge-small-en-v1.5`) + Gemini (`google-genai`) → Render
- **Data:** Supabase (Postgres + pgvector, Auth, private Storage)

Specs: [project.md](project.md) (what) · [architecture.md](architecture.md) (how) · [DECISIONS.md](DECISIONS.md) (choices made while building).

```
supabase/migrations/001_init.sql   schema, RLS, bucket, RPC functions
backend/                           FastAPI app, worker, tests
frontend/                          React SPA
.github/workflows/keepalive.yml    twice-weekly ping so Supabase/Render don't go cold
```

## 1. Supabase setup

1. Create a Supabase project.
2. Open the **SQL editor** and run all of `supabase/migrations/001_init.sql`. This creates the tables, RLS policies, the private `resumes` bucket, and the RPC functions (executable only by the service role).
3. Then run `supabase/migrations/002_admin.sql`. It adds approval and admin roles (see "Admin panel" below). Before running it, set the email in its "First admin" section to your own account.
4. **Auth → Providers → Email:** enable the Email provider. For development turn **off** "Confirm email". In production, turn it on.
5. **Project settings → API:** copy the project URL, the `anon` key (frontend), and the `service_role` key (backend only).

## 2. Backend (local)

```bash
cd backend
python -m venv .venv
.venv/Scripts/activate        # Windows; use `source .venv/bin/activate` on macOS/Linux
pip install -r requirements-dev.txt
cp .env.example .env          # fill SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, GEMINI_API_KEY
python scripts/download_embedding_model.py
uvicorn app.main:app --reload --port 8000
```

`GEMINI_API_KEY` comes from Google AI Studio. Check that `GEMINI_MODEL` names a model that is currently available. All variables are documented in `backend/.env.example` and architecture.md §4.1.

Lint and tests:

```bash
ruff check .
pytest
```

`tests/test_isolation.py` runs only when `TEST_SUPABASE_URL` and `TEST_SUPABASE_SERVICE_ROLE_KEY` point at a **separate** test project that has the migration applied.

## 3. Frontend (local)

```bash
cd frontend
npm install
cp .env.example .env          # VITE_SUPABASE_URL, VITE_SUPABASE_ANON_KEY, VITE_API_BASE_URL
npm run dev
```

Open http://localhost:5173. Other scripts: `npm run lint`, `npm test` (vitest), `npm run build`.

## 4. Deployment

### Backend → Render (free web service)
Use `render.yaml` (Blueprint) or create the service manually:
- Root directory `backend`, env `PYTHON_VERSION=3.12`
- Build: `pip install -r requirements.txt && python scripts/download_embedding_model.py`
- Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Health check path: `/health`
- Set all backend env vars. `FRONTEND_ORIGINS` must include your Vercel URL.

### Frontend → Vercel
- Root directory `frontend`, framework preset Vite, build `npm run build`, output `dist`
- Env: `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`, `VITE_API_BASE_URL` (Render URL), and optionally the `VITE_MAX_*` values
- `vercel.json` already rewrites all routes to `index.html`

### Keep-alive
Add the repo secret `BACKEND_URL` (your Render URL). `.github/workflows/keepalive.yml` calls `/health/db` on Mondays and Thursdays. Without it, a free Supabase project pauses after a week of inactivity.

## 5. How it works

- **Upload** (`POST /resumes`): each file is checked (PDF magic bytes, ≤ 1 MB, ≤ 2 pages, not encrypted, not a duplicate in *your* library, free slots out of 500). Accepted files go to Storage at `{owner_id}/{resume_id}.pdf` with status `pending`, and the request returns 202 right away.
- **Worker** (one asyncio loop in the API process): claims the next pending resume, extracts the text with PyMuPDF, has Gemini extract structured fields, computes total experience in code (overlaps merged), normalizes skills, then builds and embeds the chunks. It is resumable: on startup, resumes stuck in `processing` for more than 10 minutes go back to `pending`.
- **Search** (`POST /search`): Gemini turns the prompt into filters, a semantic query, criteria to verify, and any ignored parts. One SQL function applies the filters and vector similarity to the caller's own resumes. If nothing matches, filters are relaxed one by one and the UI says which. Gemini then checks the top 15 candidates and explains each match. If Gemini is unavailable, results are ranked by similarity and the UI says so.

## Admin panel

- **New sign-ups wait for approval.** After signing up, a user sees "Waiting for approval" until an admin approves them. The screen re-checks automatically.
- **`/admin`** (admins only, linked as "Admin panel" in the top bar) has three lists:
  - **Pending requests:** Approve or Reject.
  - **Active users:** resume counts, last sign-in, **View as user**, **Revoke access**.
  - **Rejected:** can be approved again.
- **View as user** opens that user's Resumes and Search pages **read-only**. An orange "VIEWING AS ADMIN — user@email" bar stays at the top, with an Exit link. Upload, delete and retry are hidden, and the API refuses them.
- **To add another admin**, run this in the SQL editor: `update public.profiles set role = 'admin', status = 'approved' where email = 'someone@example.com';`

## 6. Privacy and data isolation

- Every table has `owner_id`. Every backend query filters by the user id taken from the verified token. Another user's resume returns 404. RLS is enabled as a second layer of defense.
- PDFs are never public. They are reached only through 1-hour signed URLs, issued after an ownership check.
- The service-role key and the Gemini key exist only on the backend. Logs contain ids and status changes, never resume text, emails, or phone numbers.
- **Gemini free tier:** Google may use free-tier API inputs to improve its models. **Real candidate data requires a paid Gemini API key.**

## 7. Storage note

A full library is at most 500 × 1 MB = 500 MB per user. A free Supabase project (1 GB Storage) can therefore hold about two completely full libraries. Typical 2-page resumes are much smaller than 1 MB.

## 8. Known limitations (MVP)

- No OCR: scanned or image-only PDFs end in `failed` with "No readable text found."
- PDF only (no DOCX or images). Limits: 1 MB and 2 pages per file, 20 files per upload, 500 resumes per user.
- No campaigns, folders, tags, sharing, or team workspaces. The only roles are user and admin, and admins can view other libraries read-only.
- The search rate limit (30/min per user) is in memory, so it resets on restart.
- The Render free instance sleeps after about 15 minutes idle; the UI shows a "Starting the server…" banner while it wakes up. While resumes are processing, the UI polls every 3 s, which keeps the instance awake until the queue drains.
