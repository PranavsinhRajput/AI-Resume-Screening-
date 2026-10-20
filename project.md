# Resume Screening AI — Project Specification

> **Audience:** an AI coding agent that will build this application end to end.
> **Rule for the agent:** everything you need is specified in this file and `architecture.md`. If something is genuinely not specified, choose the simplest option, implement it, and list the choice in a `DECISIONS.md` file at the repo root. Do not silently skip a requirement.
> **Companion file:** `architecture.md` (tech stack, folder structure, database SQL, API contracts, prompts, theme, deployment).

---

## 1. Problem statement

A company receives a large number of resumes (PDF) during hiring. The HR / recruiting team cannot read them all. Build a web application where HR:

1. Uploads many resumes (PDF) into their **resume library** (one flat list of all saved resumes, max **500** per user).
2. Types a request in **plain language**, for example:
   - "Give me the relevant resumes for the AI Engineer role"
   - "Show resumes with at least 2 years of experience"
   - "Python developers who have deployed ML models to production"
   - "Freshers with React projects"
3. Gets back a **ranked list of relevant resumes**, each with a short explanation of why it matched, evidence from the resume, and a button to open the original PDF.

The application parses every resume, stores it in structured form plus semantic embeddings, and answers each prompt by combining exact filters (SQL), semantic search (pgvector), and LLM verification.

## 2. Decisions already made (do NOT re-decide)

| Area | Decision |
|---|---|
| Frontend | React + **JavaScript (ES modules, JSX — no TypeScript)** + Vite + Tailwind CSS. **Must be fully responsive** (mobile, tablet, desktop). |
| Theme | Harvest-orange design tokens with a **light and a dark theme** (exact CSS in `architecture.md` §10.1). |
| Backend | Python FastAPI |
| PDF text extraction | PyMuPDF (`pymupdf`) |
| Database / Auth / Storage / Vectors | **Supabase only**: Postgres (SQL tables), pgvector (embeddings), Supabase Auth (email + password), Supabase Storage (PDF files) |
| Embeddings | Hugging Face model `BAAI/bge-small-en-v1.5` (384 dimensions), run locally via `fastembed` (ONNX). Details in `architecture.md`. |
| LLM | Google Gemini via the `google-genai` Python SDK (Gemini API free tier, model name from env var) |
| Backend hosting | Render free web service |
| Frontend hosting | Vercel |
| Multi-user | Multiple HR users share one deployment; **each user's data is fully isolated** |
| Organization of resumes | **No campaigns, folders, or tags.** Each user has exactly one library containing all their saved resumes, capped at **500 resumes per user**. |
| Upload limits | **1 MB per PDF, 2 pages per PDF**, max 20 files per upload request |

## 3. Goals and non-goals

**Goals (MVP — must be built):**
- Email/password sign-up and login.
- One resume library per user: list all saved resumes (max 500).
- Bulk upload PDF resumes into the library; background parsing with visible status.
- Natural-language search across the whole library; ranked results with explanations.
- Open original PDF securely.
- Strict per-user data isolation.
- Responsive UI with light and dark themes.

**Non-goals for MVP (do NOT build; listed in section 14 as Phase 2):**
- Campaigns, folders, tags, or any other grouping of resumes.
- OCR for scanned/image-only PDFs (reject them with a clear message).
- Word/DOCX or image resumes (PDF only).
- Team workspaces / sharing resumes between users / admin role.
- Email sending, calendar, ATS integrations.
- Internationalization.
- Resume editing.

## 4. Users and roles

- **HR user**: the only role. Signs up with email + password. Owns one resume library. Can see **only** their own resumes, searches, and files.
- No admin, no super-user, no shared data. Two HR users must never see each other's data, even if they upload the identical file.

## 5. Glossary

- **Library**: all resumes a user has saved (max 500). There is exactly one per user and it is created implicitly; the user never creates or names it.
- **Resume**: one uploaded PDF and its parsed data.
- **Chunk**: a small piece of resume text (~200–350 words) with an embedding vector. Many per resume.
- **Search**: one natural-language prompt run against the user's whole library.
- **Filter**: an exact condition applied in SQL (e.g. experience ≥ 24 months).
- **Verify criterion**: a free-form condition checked by the LLM against resume text (e.g. "has led a team").

## 6. Functional requirements

### 6.1 Authentication (FR-AUTH)
- FR-AUTH-1: Sign up with email + password (min 8 chars) via Supabase Auth from the frontend (`supabase-js`).
- FR-AUTH-2: Login, logout. Session persists across page reloads (supabase-js default storage).
- FR-AUTH-3: If Supabase email confirmation is enabled, after sign-up the UI shows "Check your email to confirm your account" instead of redirecting. If a session is returned immediately, redirect to `/resumes`.
- FR-AUTH-4: All pages except `/login` and `/signup` require a session; otherwise redirect to `/login`.
- FR-AUTH-5: Every backend request (except `GET /health` and `GET /health/db`) requires `Authorization: Bearer <supabase access token>`. Missing/invalid token → HTTP 401.
- FR-AUTH-6: On any 401 response the frontend signs the user out and redirects to `/login` with a message "Your session expired. Please log in again."

### 6.2 Resume library (FR-LIB)
- FR-LIB-1: Every user has exactly one library: the set of all their resumes. There is no setup step, no naming, and no grouping.
- FR-LIB-2: A user may store at most **500 resumes** (env `MAX_RESUMES_PER_USER`, default 500). Every status (`pending`, `processing`, `done`, `failed`) counts toward the limit.
- FR-LIB-3: The UI always shows usage as "N / 500 resumes".
- FR-LIB-4: If an upload would exceed the limit, files that fit are accepted in order and the remaining files are rejected with reason `library_full` and the message "Library is full (500 resumes). Delete some resumes to add more." When the library is full, the upload area is disabled and shows the same message.
- FR-LIB-5: Deleting a resume (FR-RES-5) frees a slot immediately.
- FR-LIB-6: The backend exposes per-status counts (`total`, `done`, `pending`, `processing`, `failed`, `limit`) through one stats endpoint (`architecture.md` §6.1).

### 6.3 Resume upload (FR-UP)
- FR-UP-1: Upload one or many PDF files at once (drag-and-drop area plus a file picker button; the picker allows multiple selection).
- FR-UP-2: Limits (configurable via env, defaults): max **1 MB** per file, max **20 files** per upload request, max **2 pages** per PDF, max **500 resumes** in the library (FR-LIB-2).
- FR-UP-3: Per-file validation at upload time (before storing). A file is **rejected** with a specific reason if:
  - it is not a PDF (check extension `.pdf` AND the first bytes are `%PDF`) → reason `not_a_pdf`;
  - it exceeds the size limit → `file_too_large`;
  - PyMuPDF cannot open it or it is corrupted → `corrupted_pdf`;
  - it is password-protected → `password_protected`;
  - it has more than the max pages → `too_many_pages`;
  - the same file content (SHA-256) already exists **in the user's library** (or earlier in the same request) → `duplicate` (include the existing resume's id when there is one);
  - the library has no free slot left → `library_full`;
  - it is beyond the per-request file limit → `too_many_files`.
  Rejected files do not stop the other files in the same request from being accepted.
- FR-UP-4: Accepted files are stored in Supabase Storage, a `resumes` row is created with `status = 'pending'`, and the HTTP response returns immediately (HTTP 202) listing accepted and rejected files. Parsing happens in the background (section 6.4).
- FR-UP-5: The UI shows, per file: filename, upload progress, then the accepted/rejected result with the reason in plain language. Obvious violations (over 1 MB, more than 20 files, not enough free slots) are also pre-checked on the client with an immediate message.
- FR-UP-6: Deduplication is **per user library only**. The same file may be uploaded by two different users.

### 6.4 Background processing (FR-PROC)
For each `pending` resume the background worker performs, in order:
1. Load PDF bytes from Storage.
2. Extract text with PyMuPDF (reading order preserved, see `architecture.md`).
3. If the extracted text has fewer than 200 characters → mark `failed` with message "No readable text found. Scanned/image-only PDFs are not supported yet."
4. Call Gemini to extract structured data (JSON schema in `architecture.md`).
5. Compute `total_experience_months` **in code** (never by the LLM) using section 7.
6. Normalize skills (lowercase, alias map).
7. Save structured data into `resumes` and `experiences`.
8. Build chunks (structured chunks + raw-text windows), embed them with the embedding model, save to `resume_chunks`.
9. Set `status = 'done'`.

Rules:
- FR-PROC-1: Status lifecycle: `pending → processing → done` or `failed`. A failed resume stores `error_message` (user-readable).
- FR-PROC-2: The worker must be **resumable and idempotent**. The Render free instance sleeps and restarts; on startup, any resume stuck in `processing` for more than 10 minutes is reset to `pending`. Re-running processing for a resume first deletes its existing experiences and chunks.
- FR-PROC-3: The worker must respect Gemini rate limits (concurrency and minimum interval between calls are env-configurable) and retry 429/503/timeouts with exponential backoff (max 5 attempts). After final failure → `failed` with message "AI service busy. Please retry."
- FR-PROC-4: A failure in one resume never affects others.
- FR-PROC-5: The user can **retry** a failed resume (button → `POST /resumes/{id}/retry`), which sets it back to `pending`.
- FR-PROC-6: Resume text is untrusted input. Treat it strictly as data (prompt-injection defense, see `architecture.md` prompts).

### 6.5 Resume list and detail (FR-RES)
- FR-RES-1: The "Resumes" tab lists the user's resumes (paginated, 20 per page, newest first) with: candidate name (or filename if not yet parsed), status badge, total experience, top skills, upload time. Filter by status. A usage indicator "N / 500 resumes" is shown above the list (FR-LIB-3).
- FR-RES-2: While the library has any `pending` or `processing` resume (determined from the stats endpoint, not only the visible page), the list and stats auto-refresh every 3 seconds; stop polling when none remain.
- FR-RES-3: Clicking a resume opens a detail view (side drawer on desktop, full-screen sheet on mobile) showing: name, email, phone, location, links, summary, skills, experiences (title, company, dates, description), education, certifications, parse warnings, and an **Open PDF** button.
- FR-RES-4: **Open PDF**: the frontend calls `GET /resumes/{id}/download-url`, receives a signed URL valid for 1 hour, and opens it in a new tab. PDFs are never publicly accessible.
- FR-RES-5: Delete a single resume (confirmation required). Removes the DB rows and the Storage file.

### 6.6 Natural-language search (FR-SRCH)
- FR-SRCH-1: In the "Search" tab, a text box (3–500 chars) and a Search button. Show 3 example prompt chips that fill the box when clicked.
- FR-SRCH-2: A search only considers the user's resumes with `status = 'done'`. If there are none → show "Upload and process resumes first."
- FR-SRCH-3: Search pipeline (details in `architecture.md`):
  1. **Parse the prompt** with Gemini into: `filters`, `semantic_query`, `verify_criteria`, `unsupported`, `interpretation`.
  2. **Retrieve** candidates with one SQL function call: hard filters + vector similarity, returning the best 15 resumes.
  3. **Verify & explain** with Gemini: for those 15 candidates (structured summary + top matching chunks), check each verify criterion with evidence, score role fit 0–100, write a 1–2 sentence reason.
  4. **Rank and return** results.
- FR-SRCH-4: Always show the user how the prompt was interpreted ("Searching for: experience ≥ 2 years · AI engineer") in a banner above results, so HR can correct a misread by rephrasing.
- FR-SRCH-5: Result card shows: rank, candidate name, experience (e.g. "3 yrs 4 mos"), location, top skills (chips), match score (0–100), reason, a checklist of verify criteria (✓ met / ✗ not met / ? unknown) with the evidence snippet, **View resume** button (opens PDF as in FR-RES-4) and **Details** button (opens the detail view).
- FR-SRCH-6: Results where every *required* verify criterion is met appear first, ranked. Results that fail a required criterion appear under a collapsed section "Partial matches" (max 5), clearly marked. Nothing is silently dropped for criteria the LLM could not verify.
- FR-SRCH-7: **Zero results fallback:** if the first retrieval returns nothing, relax filters automatically in this order — `location`, `required_skills`, `max_experience_months`, `min_experience_months` — retrying after each removal, and show a notice: "No exact matches. Relaxed: location." Never relax silently.
- FR-SRCH-8: **Unsupported/discriminatory criteria:** if the prompt asks to filter or rank by gender, age, religion, caste, marital status, nationality, ethnicity, disability, or photo, those parts are **ignored**, and the banner says so ("Ignored: 'only male candidates' — the system doesn't filter on personal attributes."). The rest of the prompt is still executed. Names/gender/age must never influence ranking.
- FR-SRCH-9: **Vague role-less prompts** ("show me the best resumes") have no role or skills to search for, so the raw prompt text is used as the semantic query and the banner states this: "Your request didn't name a role or skills, so these are the closest matches to your wording. Try naming a role or skills for better results."
- FR-SRCH-10: **Graceful LLM failure:** if the verify step fails after retries (rate limit/timeout), return results ranked by vector similarity with deterministic reasons ("Matched on: <best snippet>") and `llm_degraded: true`; the UI shows a notice "AI explanations are temporarily unavailable; results are ranked by similarity."
- FR-SRCH-11: If the prompt-parsing step itself fails after retries, fall back to using the raw prompt as `semantic_query` with no filters, and show a notice.
- FR-SRCH-12: Default `top_k` = 10 qualifying results (configurable up to 25).
- FR-SRCH-13: Light rate limit: 30 searches per minute per user (in-memory is acceptable) → HTTP 429.

## 7. Experience calculation rules (implemented in code)

- Input: the list of `experiences` extracted by the LLM, each with `start_date`, `end_date`, `is_current` (dates as `"YYYY-MM"` or `"YYYY"` or null).
- Count **all** employment types (full-time, part-time, internship, contract, freelance, unknown). Do not count projects or education.
- Date handling: `"YYYY"` start → January of that year; `"YYYY"` end → December of that year (but not later than the current month if that year is the current year). `is_current = true` or `end_date = null` with `is_current = true` → end = current month (UTC).
- If `start_date` is missing, or end is missing while `is_current` is false, or `end < start` → skip that entry and add a human-readable string to `parse_warnings` (e.g. "Skipped experience at ACME: missing end date").
- Convert each valid interval to inclusive month indexes (`year*12 + month`), **merge overlapping intervals** (so two overlapping jobs are not double-counted), and sum `(end_idx - start_idx + 1)` over merged intervals.
- Fresher with no valid experience → `total_experience_months = 0` (never null for a `done` resume).
- UI formatting: `X yrs Y mos`, e.g. 28 months → "2 yrs 4 mos"; 0 → "Fresher (0 yrs)".

## 8. Prompt interpretation rules (used by the query-parsing step)

| HR wording | Parsed as |
|---|---|
| "N years of experience", "N+ years", "at least N years" | `min_experience_months = N*12` |
| "less than N years", "up to N years" | `max_experience_months = N*12` |
| "between A and B years" | both |
| "fresher", "entry level" | `max_experience_months = 12` |
| Role names ("AI Engineer", "data analyst") | go into `semantic_query`, never into filters |
| Skills phrased as mandatory ("must know Python", "with Python", "who know Python", "required: SQL") | `required_skills` (hard SQL filter, normalized) |
| Skills phrased as optional ("preferably", "bonus", "nice to have") | `preferred_skills` (soft; added to semantic query) |
| City/region ("from Pune", "based in Bangalore") | `location` filter (case-insensitive substring) |
| Abstract/free-form conditions ("has led a team", "worked in fintech", "has open-source contributions", "deployed ML models") | `verify_criteria` (LLM-verified) **and** included in `semantic_query` |
| "not X" / "without X" | a `verify_criteria` item with `required: true` phrased as a negative ("does not have only service-company experience") — semantic search cannot do negation |
| Personal attributes (gender, age, religion, caste, marital status, nationality, ethnicity, disability, photo) | `unsupported` (ignored) |
| "culture fit", "good attitude", other things a resume cannot show | `unsupported` with reason "cannot be determined from a resume" |

Interpretation is shown to the user (FR-SRCH-4). Experience filters mean "total experience in any role", not role-specific experience (role-specific is handled by `verify_criteria`).

## 9. Data isolation requirements (critical)

- DI-1: Every table holding user data has `owner_id` referencing the Supabase auth user, and every backend query filters by the `owner_id` taken from the **verified token** — never from request bodies, query strings, or path parameters.
- DI-2: Accessing another user's resume by id returns **404** (not 403), so existence is not leaked.
- DI-3: Vector search always includes the `owner_id` condition in the same SQL statement as the similarity search.
- DI-4: Storage bucket is private. Object paths are `{owner_id}/{resume_id}.pdf`. Files are only reachable through short-lived signed URLs issued after an ownership check.
- DI-5: Row Level Security is enabled on all tables as defense in depth (policy: `owner_id = auth.uid()`), even though the backend uses the service-role key.
- DI-6: The vector search SQL functions are executable only by the service role (revoked from `anon`/`authenticated`).
- DI-7: No cross-user caching. Any cache key must include `owner_id`.
- DI-8: The service-role key and Gemini key exist only on the backend. They never appear in frontend code, env, or logs.
- DI-9: Logs must not contain resume text, emails, or phone numbers.
- DI-10: The 500-resume limit is counted per `owner_id`; one user's usage never affects another's.

**Isolation test (must exist as an automated test, see `architecture.md`):** with two users A and B — (1) B cannot fetch, delete, retry, or get a download URL for A's resume by id (all 404), and A's resumes never appear in B's list or stats; (2) a search by B never returns A's resumes, even when A's resume is the best semantic match; (3) A's signed URL is only produced for A; (4) deleting A's resume removes A's Storage file, experiences, and chunks and does not touch B's; (5) A and B can both upload the identical file without a `duplicate` rejection.

## 10. UI specification

### 10.1 Routes
| Route | Page | Auth |
|---|---|---|
| `/login` | Login form | public |
| `/signup` | Sign-up form | public |
| `/` | Redirects to `/resumes` | required |
| `/resumes` | Library workspace with tabs **Resumes** and **Search** (`?tab=resumes|search`; default = `resumes` if the library is empty, else `search`) | required |
| `*` | Not-found page with link to `/resumes` | — |

### 10.2 Layout and responsive behavior (mandatory)
- Mobile-first Tailwind. Test widths: 360, 414, 768, 1024, 1440 px. **No horizontal page scroll at any width.**
- Top app bar: app name, theme toggle (10.6), user email menu with Logout. On mobile the menu is a dropdown.
- Resumes tab: on `md+` a table; below `md` each resume is a stacked card.
- Search results: single-column cards at all sizes (max width ~ 4xl, centered on desktop).
- Detail view: right-side drawer on `lg+`; full-screen sheet below `lg`.
- Modals (confirm delete): centered dialog on `md+`; full-width bottom sheet on mobile.
- All interactive elements ≥ 44 px tall on touch layouts, visible focus rings, buttons have text or `aria-label`.
- Skills chips wrap; long text truncates with a "Show more" toggle; evidence snippets are clamped to 3 lines with expand.

### 10.3 Required UI states (every data view)
- **Loading:** skeleton placeholders or spinner.
- **Empty:** helpful message and the next action (e.g. "No resumes yet — drag PDFs here").
- **Error:** message from the API error `message`, with a Retry button.
- **Server waking up:** Render free instances sleep. On app load the frontend calls `GET /health`; if it has not responded within 2.5 s, show a banner "Starting the server — this can take up to a minute on free hosting…" and keep retrying (timeout 90 s). Hide the banner on success. Any later request that takes > 5 s also shows the banner until it completes.
- **Processing:** resume status badges: `Queued` (pending), `Processing…` (spinner), `Ready` (done), `Failed` (with message + Retry).
- **Library full:** upload area disabled with the FR-LIB-4 message.
- **Search in progress:** show progress text ("Understanding your request… → Finding resumes… → Checking details…"). These are cosmetic stages on the client (the API is one call).

### 10.4 Search results card (exact content)
```
[#1]  Candidate Name                         Match 87
3 yrs 4 mos · Pune                    [Open PDF] [Details]
Python · PyTorch · FastAPI · NLP · +6
Reason: Built and deployed an NLP pipeline in production at X; 3+ years in ML roles.
Criteria:  ✓ 2+ years experience   ✓ Deployed ML models ("deployed a FastAPI model service on AWS…")
```
Name falls back to the filename if no name was extracted.

### 10.5 Library usage indicator
Above the resume list and inside the upload area: "N / 500 resumes" with a thin progress bar (uses `--color-accent` on `--color-soft-accent`). At ≥ 90 % usage the text switches to a warning style; at 100 % the upload area is disabled (FR-LIB-4).

### 10.6 Theme (mandatory)
- The visual design uses the **Harvest Orange token set** defined verbatim in `architecture.md` §10.1, with a light theme (default tokens) and a dark theme (`[data-theme="dark"]`).
- A theme toggle (sun/moon icon button, `aria-label` "Switch to dark theme" / "Switch to light theme") sits in the app bar and also on the login/signup pages.
- First visit follows the OS preference (`prefers-color-scheme`); afterwards the user's choice is remembered in `localStorage`. The theme is applied before first paint (no flash of the wrong theme).
- No hard-coded colors in components: every surface, text, border, accent and shadow comes from the tokens. The only exceptions are semantic status colors (success / error / warning), which must have readable light and dark variants.
- Both themes must pass the same responsive and accessibility requirements (visible focus rings, readable contrast).

## 11. Non-functional requirements

- NFR-1 **Free-tier friendly:** must run on Render free (512 MB RAM, sleeps after 15 min idle), Supabase free (500 MB DB, 1 GB storage), Gemini API free tier, Vercel free. Storage note for the README: a full library is at most 500 × 1 MB = 500 MB per user, so a free 1 GB project can hold roughly two completely full libraries; typical 2-page resumes are far smaller than 1 MB.
- NFR-2 **Performance targets (warm server):** list endpoints < 500 ms; search < 12 s end to end (two Gemini calls + SQL); processing ~10–30 s per resume depending on rate limiting.
- NFR-3 **Privacy:** resumes contain personal data. The doc must note in `README.md` that the Gemini **free** tier may use inputs to improve Google's models, so real candidate data requires a paid Gemini key.
- NFR-4 **Reliability:** no unhandled exceptions leak stack traces to clients; all errors use the JSON error format in `architecture.md`.
- NFR-5 **Accessibility:** semantic HTML, labels on inputs, `aria-live="polite"` for status changes and search progress.
- NFR-6 **Code quality:** type hints throughout the backend and `ruff` for backend lint. The frontend is plain JavaScript (no TypeScript): ESLint, JSDoc `@typedef`s for API shapes in `lib/types.js`, and no unexplained `eslint-disable` comments.

## 12. Error handling catalog

| Situation | HTTP | `error.code` | User-facing message |
|---|---|---|---|
| Missing/invalid token | 401 | `unauthorized` | Your session expired. Please log in again. |
| Resource not found or not owned | 404 | `not_found` | We couldn't find that. |
| Validation error | 422 | `validation_error` | Field-specific message |
| Search with no processed resumes | 409 | `no_resumes_ready` | Upload and process resumes first. |
| Too many searches | 429 | `rate_limited` | Too many searches. Try again in a minute. |
| Upload: bad file or library full | 202 with entry in `rejected[]` | per-file `reason` (see FR-UP-3) | Plain-language message per reason |
| Unexpected server error | 500 | `internal_error` | Something went wrong. Please try again. |

## 13. Acceptance criteria (the app is "done" for MVP when all pass)

1. Sign up, log in, log out, session survives reload; protected pages redirect when logged out.
2. Upload 12 mixed PDFs in one go, including: one duplicate, one non-PDF renamed `.pdf`, one scanned/image-only PDF, one password-protected PDF, one PDF larger than 1 MB, one PDF with 3 pages. Result: those files are rejected with the correct reasons (`duplicate`, `not_a_pdf`, `password_protected`, `file_too_large`, `too_many_pages`); the scanned PDF is accepted but ends `failed` with the "No readable text" message; the rest become `done`.
3. Resumes list auto-updates while processing and stops polling when finished.
4. Restarting the backend mid-processing: stuck resumes return to `pending` and complete.
5. Search "resumes with at least 2 years of experience" → banner shows `experience ≥ 24 months`; only matching resumes returned; sorted sensibly.
6. Search "relevant resumes for the AI engineer role" → ranked list with reasons and snippets.
7. Search "candidates who have led a team and know Python" → `required_skills: [python]` filter plus a verify criterion with ✓/✗ and evidence.
8. Search "only male candidates with 3 years experience" → gender part ignored with banner notice; experience filter applied.
9. Search that yields zero results with a strict filter → relaxed automatically with a visible notice.
10. Open PDF works via signed URL; the raw Storage URL without a signature fails.
11. Isolation tests (section 9) pass with two accounts.
12. Library limit: with `MAX_RESUMES_PER_USER` set to a small number in a test environment, uploading more files than free slots accepts only the files that fit and rejects the rest with `library_full`; deleting a resume frees a slot; the UI shows "N / limit" and disables the upload area when full.
13. Delete a resume → its rows and Storage file are gone.
14. UI usable at 360 px width with no horizontal scroll; tables become cards.
15. Theme: the toggle switches between light and dark using the token set; the choice persists across reloads; first load follows the OS preference; no flash of the wrong theme; both themes look correct on every page.
16. With an invalid Gemini key, upload still succeeds, resumes end `failed` with a clear message, and the app does not crash.

## 14. Phase plan

**Build order (MVP):**
1. Supabase schema + bucket + RLS + SQL functions (`architecture.md` §5).
2. Backend skeleton: config, auth dependency, error format, health endpoints.
3. Upload + validation (1 MB / 2 pages / 500-resume limit) + Storage + background worker with PyMuPDF extraction; list/detail/stats/download/delete/retry endpoints.
4. Gemini extraction, experience calculation, skills normalization, chunking, embeddings.
5. Query parsing, retrieval SQL, verification, ranking, relaxation, degraded modes.
6. Frontend: theme tokens, auth, upload + status, resume list/detail, search + results.
7. Responsive polish, error/empty/loading states, cold-start banner, dark theme pass.
8. Tests, `README.md`, deployment configs, keep-alive workflow.

**Phase 2 (do not build now):** campaigns or folders to group resumes; shortlist/star candidates and CSV export; follow-up refinement of the previous search ("now only from Pune"); paste a job description as the query; OCR for scanned PDFs; role-specific experience; DOCX support; fair queueing across users; team workspaces; raising the 1 MB / 2-page / 500-resume limits.
