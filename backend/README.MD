The chat endpoint does not fabricate assistant content. Until a real AI provider is configured, chat requests return HTTP `503` with a provider-unavailable error, which the frontend displays as an error state.

## Data Collection (Phase D — Real Sources)

The collection workflow fetches real records from an explicit allow-list of permitted sources. The deterministic fake collector has been removed.

**Permitted sources** (each verified for robots.txt compliance and terms of use):

| Domain | Entity | Kind | Rate limit |
| --- | --- | --- | --- |
| `books.toscrape.com` | product | static HTML (scraping sandbox) | 0.5 req/s |
| `www.arbeitnow.com` | job | keyless public job-board API | 0.5 req/s |
| `hn.algolia.com` | record | official Hacker News Search API | 1 req/s |

**Policy enforcement** — every outbound request goes through `app/tools/fetcher.py`, which refuses any domain not on the allow-list in `app/tools/source_policy.py`, fetches and caches each domain's `robots.txt` (1 hour TTL; a `403` robots response blocks the whole domain), consumes one token from a per-domain token bucket before fetching, and stamps results with the real retrieval timestamp. `ProvenanceEntry.sourceUrl` and `retrievedAt` now come from actual HTTP responses.

**Pipeline** — the planner over-fetches raw records (2x the requested count, capped at 8 rounds) because validation drops records that fail constraints such as price caps; the search → extract → validate → deduplicate loop repeats until enough valid records exist or the source runs dry, then reports `COMPLETED` or `PARTIAL` — it never fabricates records to fill a gap. Search prompts are reduced to clean search terms before hitting search APIs.

**No browser automation** — all permitted sources are static HTML or JSON APIs, so the pipeline uses `httpx` + `beautifulsoup4` only. Playwright is intentionally not included. JS-gated pages (e.g. `python.org/events`) were evaluated and rejected for this reason.

**Adding a source** — add the domain to `PERMITTED_SOURCES` in `app/tools/source_policy.py` with its entity, kind (`html` or `api`), and rate limit; verify its `robots.txt` actually permits collection first; then add an adapter in `app/tools/sources.py` and register its planning capacity in `app/tools/registry.py`.

Set `COLLECTOR_USER_AGENT` (see `.env.example`) to control the User-Agent sent by the collector; `robots.txt` is evaluated for this agent.
# VaultPulse.AI Backend

The backend is a separate FastAPI project. It owns authentication, API contracts, validation, user data access, document indexing, chat, and collection task state. Frontend-specific rules live in `../frontend/codex.md`; backend rules live in `codex.md`.

## Run Locally

```powershell
cd backend
.\venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The API runs at `http://localhost:8000`. Set `LOG_LEVEL` to control backend console logging; it defaults to `INFO`.

## Deploy To Vercel

The FastAPI app has a Vercel entrypoint at `api/index.py`. Create a separate Vercel project from this repository with the project root set to `backend`; Vercel will detect the Python function from that file. Configure these environment variables in the Vercel project:

```text
DATABASE_URL=postgresql://postgres.project-ref:password@aws-0-region.pooler.supabase.com:6543/postgres?sslmode=require
CORS_ORIGINS=https://your-frontend-domain.vercel.app
AI_PROVIDER_API_KEY=your-key
AI_PROVIDER_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/chat/completions
AI_MODEL=gemini-2.5-flash
```

Deploy the backend first, set `NEXT_PUBLIC_API_URL` in the frontend Vercel project to the backend URL, then deploy the frontend. Do not put secrets in `NEXT_PUBLIC_*` variables.

Vercel functions are stateless and request-limited. Collection datasets are persisted in the `collection_tasks.dataset` JSONB column; the backend does not rely on local dataset or UI files. Collection jobs still use background threads and SSE, so run them on a persistent backend host or migrate them to a durable queue before relying on long-running collection jobs in production.

Set `DATABASE_URL` to the Supabase pooler connection string from Project Settings -> Database. For Vercel, choose the IPv4-compatible pooler connection and use its `aws-*.pooler.supabase.com` host, usually port `6543`; do not use the direct `db.<project-ref>.supabase.co` host because it may resolve only to IPv6. Use the URI exactly as Supabase provides it, including `sslmode=require`. On startup, the backend applies the idempotent SQL migrations in order and uses a bounded `psycopg` connection pool. The frontend does not connect to Supabase directly.

## Chat Provider

Chat uses an OpenAI-compatible HTTP API. The API key can come from any service that supports this request and response format. `AI_PROVIDER` is only an optional label; the endpoint determines compatibility. Copy these settings into `backend/.env`, set a real API key, then restart FastAPI:

```text
AI_PROVIDER=
AI_PROVIDER_API_KEY=your-key
AI_PROVIDER_BASE_URL=https://api.openai.com/v1/chat/completions
AI_MODEL=gpt-4o-mini
APP_TIMEZONE=Asia/Kolkata
AI_LIVE_SEARCH_ENABLED=true
```

A missing key or unreachable/incompatible endpoint returns `503`; the backend never creates a fabricated assistant response. Chat requests include the current backend date and time in `APP_TIMEZONE` (default `Asia/Kolkata`) so the model does not fall back to a training snapshot. When `AI_PROVIDER_BASE_URL` uses `generativelanguage.googleapis.com`, chat uses Gemini's native Google Search grounding and includes returned source links in the answer. This uses the existing Gemini API key; set `AI_LIVE_SEARCH_ENABLED=false` to disable it. For other OpenAI-compatible providers, live web search is not enabled and the model must not invent current facts. Search grounding usage may incur provider charges.

## Validation And Logging

Pydantic schemas reject whitespace-only messages, prompts, and titles, normalize accepted text, enforce non-negative provenance indexes, and require dataset counts to match the number of records. Route and service logs report resource IDs, owner IDs, statuses, counts, lengths, and event names. Passwords, bearer tokens, full prompts/messages, and uploaded file contents are never logged.

## Change Log

### 2026-09-27

| Change | Reason | Effected files |
| --- | --- | --- |
| Added schema-level validation for chat, conversation, and collection payloads. | Reject invalid data before business logic runs. | `app/schemas/chat.py`, `app/schemas/conversation.py`, `app/schemas/collection.py` |
| Added dataset count and provenance constraints. | Prevent inconsistent or unusable collection results. | `app/schemas/collection.py` |
| Added lifecycle logging for conversations, chat, uploads, and collections. | Trace every important data/state update without exposing sensitive data. | `app/main.py`, `app/routes/`, `app/services/` |
| Added an OpenAI-compatible provider adapter. | Return real assistant responses when configured, without mock data. | `app/services/chat_service.py`, `.env.example` |
| Added Supabase Postgres persistence for users, sessions, conversations, messages, documents, and collection tasks/events. | Prevent data loss on backend restart and enforce database ownership constraints. | `app/db.py`, `migrations/001_initial.sql`, `app/services/`, `app/routes/collections.py`, `requirements.txt` |

### 2026-09-28

| Change | Reason | Effected files |
| --- | --- | --- |
| Replaced the deterministic fake collector with real permitted sources (scraping sandbox + keyless public APIs). | Phase D: collection results and provenance must reflect real HTTP responses, not synthetic data. | `app/tools/registry.py`, `app/tools/sources.py`, `app/tools/fetcher.py`, `app/ai/graph.py` |

### 2026-09-29

| Added optional client message IDs with a unique per-conversation, per-role index so retries do not create duplicate chat rows. | Provider failures occur after saving the user message; retrying should reuse that saved message. | `migrations/003_message_idempotency.sql`, `app/schemas/chat.py`, `app/services/conversation_service.py`, `app/routes/chat.py` |
| Added the runtime date and time to chat system instructions, configurable with `APP_TIMEZONE`, and directed the model not to invent ungrounded current facts. | Prevent answers from presenting the model's training snapshot as today's date or fabricating time-sensitive statistics. | `app/services/chat_service.py`, `.env.example` |
| Give default conversations a title from their first user message; retain owner-scoped history listing. | Make each account's sidebar history identifiable while preserving conversation ownership checks. | `app/services/conversation_service.py` |
| Added a real source policy: explicit domain allow-list, robots.txt fetch/cache/enforcement, per-domain token-bucket rate limits. | Respect terms, access restrictions, and rate limits before any fetch. | `app/tools/source_policy.py`, `app/tools/fetcher.py` |
| Added over-fetch planning and count capping; clean search-term extraction from prompts. | Validation drops failing records, so plan raw volume above target and deliver exactly what was requested. | `app/ai/planner.py`, `app/ai/requirement_analyzer.py`, `app/workflow/executor.py` |
| Removed the fake collector and its source ceiling. | Fake source keys and synthetic provenance are no longer part of the pipeline. | `app/ai/fake_collector.py` (deleted), `app/ai/requirement_analyzer.py` |
| Added `httpx` and `beautifulsoup4`; no Playwright. | All permitted sources are static HTML or JSON APIs; browser automation is unnecessary and heavy. | `requirements.txt` |
