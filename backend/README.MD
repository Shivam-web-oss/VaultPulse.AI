The chat endpoint does not fabricate assistant content. Until a real AI provider is configured, chat requests return HTTP `503` with a provider-unavailable error, which the frontend displays as an error state. The collection workflow still contains a deterministic fake collector for development pipeline work; it must not be presented as production dashboard data.
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

Vercel functions are stateless and request-limited. The chat and document routes are suitable for this entrypoint, but collection jobs currently use background threads, SSE, and local `runtime/tasks` files. Run those workflows on a persistent backend host or migrate them to a durable queue and object storage before relying on collections in production.

Set `DATABASE_URL` to the Supabase pooler connection string from Project Settings -> Database. For Vercel, choose the IPv4-compatible pooler connection and use its `aws-*.pooler.supabase.com` host, usually port `6543`; do not use the direct `db.<project-ref>.supabase.co` host because it may resolve only to IPv6. Use the URI exactly as Supabase provides it, including `sslmode=require`. On startup, the backend applies the idempotent `migrations/001_initial.sql` migration and uses a bounded `psycopg` connection pool. The frontend does not connect to Supabase directly.

## Chat Provider

Chat uses an OpenAI-compatible HTTP API. The API key can come from any service that supports this request and response format. `AI_PROVIDER` is only an optional label; the endpoint determines compatibility. Copy these settings into `backend/.env`, set a real API key, then restart FastAPI:

```text
AI_PROVIDER=
AI_PROVIDER_API_KEY=your-key
AI_PROVIDER_BASE_URL=https://api.openai.com/v1/chat/completions
AI_MODEL=gpt-4o-mini
```

A missing key or unreachable/incompatible endpoint returns `503`; the backend never creates a fabricated assistant response. Native provider keys that do not support the OpenAI-compatible format still require a provider-specific adapter.

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
