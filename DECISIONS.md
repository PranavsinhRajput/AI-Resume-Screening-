# Decisions

Choices not fully specified in `project.md` / `architecture.md`, recorded as required.

## Repository
- **Repo root is this folder** (`D:\Pranav`) rather than a nested `resume-screening-ai/` directory, since `project.md` and `architecture.md` already live here. The layout under it follows architecture.md §3.
- Added `render.yaml` (Render blueprint) and `.gitignore` for convenience; the Render dashboard settings in architecture.md §9.1 are equivalent.
- Added `backend/requirements-dev.txt` (pytest, pytest-asyncio, ruff) and `backend/pytest.ini` so dev tools stay out of the production install.

## Backend
- **Gemini model default:** `gemini-2.5-flash` (Flash-class, available on the free tier at the time of writing). Override with `GEMINI_MODEL`; check current Gemini docs before deploying.
- **Thinking:** requests set `thinking_config(thinking_budget=0)`. If the model rejects that (400 mentioning "thinking"), the gateway drops the setting for the rest of the process and retries.
- **Gemini structured output schemas:** Gemini's `response_schema` handles nullable unions poorly, so each LLM schema has a Gemini-only twin (`ResumeExtractionGemini`, `ParsedQueryGemini`, `VerifyResultGemini`) that uses `""` / `0` / `-1` / `"unknown"` sentinels. The answer is always validated leniently with the real Pydantic model, which converts the sentinels back to `null`. The prompts tell the model about the sentinels.
- **Verify `met` encoding:** in the Gemini schema `met` is a string (`"true"|"false"|"unknown"`), mapped back to `true|false|null`.
- **Upload rules live in `services/upload.py`** (pure function `validate_files`) so `test_upload_rules.py` can test them without network. The router only reads files, calls it, then stores accepted files.
- **Oversize detection:** the upload reader stops after `MAX_FILE_MB` + 1 byte, so a large file is never fully buffered.
- **`min_experience_months = 0`** from the parser is treated as "no filter".
- **Future end dates** in experiences are clamped to the current month.
- **Preferred skills** missing from `semantic_query` are appended to it ("Preferred skills: …"), per §8 rules ("soft; added to semantic query").
- **Requeue/claim** in `repositories/resumes.py` are the only functions without `owner_id`: they are system-level worker operations, not user requests. Processing then uses the claimed row's own `owner_id` for every query.
- **Retry on a non-failed resume** → 422 `validation_error` "Only failed resumes can be retried."
- **Non-UUID ids** in `{id}` paths → 404 (same as not owned).
- **Storage delete failures** during `DELETE /resumes/{id}` are logged and the row is still deleted, so the user is never stuck with a resume they can't remove.
- **Upload storage/insert failure for a valid file** (not a unique violation) returns 500 for the whole request; files accepted before it stay accepted.
- **Generic processing error message:** "Processing failed. Please retry." Missing Storage object: "The PDF file could not be loaded. Please delete and upload it again."
- **Embedder load** is warmed in a background thread at startup so the first search/process doesn't block the event loop.
- **Test fixtures** for unit tests are generated with PyMuPDF at test time (`tests/conftest.py`) instead of committed binaries. `tests/fixtures/README.md` lists the manual acceptance-test files.

## Admin approval & admin panel (added after MVP, on request)
This is a deliberate change from project.md §4 ("no admin role"). The user asked for it explicitly.
- **`profiles` table** (`supabase/migrations/002_admin.sql`) holds `role` (`user`|`admin`) and `status` (`pending`|`approved`|`rejected`). A trigger on `auth.users` creates a `pending` profile on every sign-up. Users who existed before the migration are backfilled as `approved`, and `official.pranavsinhrajput@gmail.com` is made the first admin.
- **Approval gate:** every resume and search endpoint requires `status = approved` and returns 403 `pending_approval` / `account_rejected` otherwise. `GET /me` works for every signed-in user and returns `role` and `status`, so the frontend can show the waiting screen. The waiting screen re-checks every 15 s.
- **Profile cache:** a 30 s TTL per user id, invalidated in-process when an admin changes that user's status. Approval and revocation therefore take effect immediately on a single Render instance.
- **"View as user" is read-only impersonation.** The admin sends `X-View-As: <user_id>`. The backend honours it only when the *verified caller* is an admin; everyone else gets 403 `forbidden`. It then scopes every query to that user's `owner_id`. Upload, retry and delete return 403 `read_only` while viewing. List, detail, stats, signed PDF URL and search are allowed. This narrows DI-1: owner_id still never comes from the client for normal users, and the header changes it only after an admin role check. Each view is logged with admin id and target id.
- **Search while viewing** counts against the admin's own rate limit, not the viewed user's.
- **Frontend caching:** query keys include the viewed user id (`['resumes', viewAsId, …]`), so an admin's own data and a viewed user's data never share cache entries (DI-7).
- **Reject vs revoke:** both set `status = 'rejected'`. "Reject" is the pending-list wording and "Revoke access" the active-list wording. A rejected user can be approved again later, and their resumes are kept. Admins can't change their own status or reject another admin.
- **Admin listing** uses the RPC `admin_list_users`, which joins profiles, `auth.users.last_sign_in_at` and per-user resume counts. Like the other RPCs it is executable only by the service role.
- **No email notification** on approval. The user's waiting screen picks it up automatically.

## Frontend
- **Tailwind token approach:** Tailwind v4 `@theme` block in `index.css` registers the token names (so `bg-app`, `text-muted`, `border-line`, `bg-accent`, `shadow-soft`, `text-harvest-orange-950`, … exist). `styles/theme.css` is unchanged from §10.1. Its rules are unlayered, so they override the `@theme` defaults at runtime, and `[data-theme="dark"]` switches the theme.
- **Dark theme attribute:** the bootstrap script and `useTheme` always set `data-theme` to `light` or `dark` (never remove it).
- **Modal scrim** uses `bg-black/40–50`, a neutral overlay rather than a surface color, in both themes.
- **Extra files:** `lib/config.js` (env-derived limits and reason messages), `pages/AuthLayout.jsx` (shared login/signup shell), `components/resumes/ResumeActions.jsx` (Open PDF / Retry / Delete shared by table, card and drawer).
- **Search state lives at page level** so results survive switching between the Resumes and Search tabs.
- **Search results:** a collapsible "Show matching excerpts" toggle shows the top snippets on each card.
- **Server-down fallback:** if `/health` keeps failing for 90 s, the banner changes to "The server is not responding. Please refresh the page in a moment."
- **Dependency versions** in `package.json` / `requirements.txt` are recent stable releases (or unpinned for Python, per §9.1). Pin them after the first successful install.
