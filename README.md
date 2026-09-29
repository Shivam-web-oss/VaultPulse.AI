<div align="center">

# VaultPulse.AI

### AI-Powered Data Intelligence Platform

Describe the data you need in plain language.
VaultPulse.AI turns that requirement into a structured, source-backed dataset — with provenance for every record.

[Live Demo](https://vault-pulse-ai.vercel.app/) · [How It Works](#how-it-works) · [API](#api-overview) · [Getting Started](#getting-started)

</div>

---

## Product Preview

<p align="center">
  <img src="docs/screenshots/landing.png" alt="VaultPulse.AI landing page" width="900" />
</p>
<p align="center">
  <sub>The VaultPulse.AI workspace — a private, account-based space for conversations and documents.</sub>
</p>

The product ships today as two halves:

- **A chat-and-document workspace** (deployed at the link above): register an account, have persistent AI-backed conversations, upload PDFs/DOCX/TXT/CSV files, and ask questions grounded in your uploads.
- **A source-aware data-collection API**: describe a dataset in natural language and a LangGraph pipeline plans the workflow, collects records from permitted sources, normalizes, validates, deduplicates, and persists them with provenance. This half is API-only right now — see [Honest Status](#honest-status).

---

## The Problem

Teams constantly need small datasets: job openings, product prices, market mentions, event listings. The data itself is rarely hard to find — the expensive part is repeating the same steps every time:

1. Figure out which sites have the data
2. Write or adapt a scraper or script
3. Clean up inconsistent fields and formats
4. Validate the results
5. Reshape everything into a spreadsheet

Each new requirement restarts the loop. VaultPulse.AI collapses it into one step: state what you need, get back a structured, traceable dataset.

```text
Natural-language requirement
        ↓
Requirement understanding (LLM, with deterministic fallback)
        ↓
Workflow planning (LangGraph)
        ↓
Collection from permitted sources
        ↓
Normalization → validation → deduplication
        ↓
Structured dataset with provenance
        ↓
Query, filter, export (JSON / CSV)
```

## How It Works

```text
┌──────────────────────────┐
│     User Requirement     │
│  "Find 20 backpacks      │
│   under 50"              │
└────────────┬─────────────┘
             ↓
┌──────────────────────────┐
│  Requirement Analysis    │  entity, count, constraints, field schema
└────────────┬─────────────┘
             ↓
┌──────────────────────────┐
│   Workflow Planning      │  tools, sources, rounds, per-round volume
└────────────┬─────────────┘
             ↓
┌──────────────────────────┐        not enough valid
│  Search → Extract        │ ──────────────────────┐
│  (permitted sources)     │                       │
└────────────┬─────────────┘                       │
             ↓                                     │
┌──────────────────────────┐                       │
│  Normalize / Validate /  │ ──── loop ────────────┘
│  Deduplicate             │
└────────────┬─────────────┘
             ↓
┌──────────────────────────┐
│  Structured Dataset      │  COMPLETED or PARTIAL — never fabricated
└────────────┬─────────────┘
             ↓
┌──────────────────────────┐
│  Query / Export (API)    │  search, filters, sort, pagination, JSON/CSV
└──────────────────────────┘
```

The planner intentionally over-fetches (2× the requested count) because validation drops records that fail constraints. The `search → extract → normalize → validate → deduplicate` loop repeats until enough valid records exist or planned rounds are exhausted. If sources run dry, the task finishes as `PARTIAL` — the pipeline never invents records to fill a gap.

---

## Key Features

**Conversational workspace (deployed)**

- **Accounts and sessions** — email/password registration with salted PBKDF2 hashing; opaque bearer tokens backed by the database.
- **Persistent conversations** — create, open, rename, delete, and auto-title conversations; history survives restarts.
- **Provider-backed chat** — any OpenAI-compatible endpoint; when a Gemini endpoint is configured, answers can use Google Search grounding and include source links.
- **Document uploads** — PDF, DOCX, TXT, and CSV up to 10 MB; text is extracted server-side and used as chat context via keyword retrieval.
- **Workspace preferences** — theme (light/dark/system), Enter-to-send, auto-scroll, timestamps; stored locally per browser.
- **Robust UI states** — skeletons, optimistic message sending, typed error banners, and one-click retry with idempotent message IDs (retries never duplicate rows).

**Data collection engine (API)**

- **Natural-language requirements** — an LLM converts arbitrary requests into a structured requirement (entity, count, constraints, field schema), with a deterministic regex fallback so the pipeline works even without a provider.
- **Dynamic workflow planning** — LangGraph decides which tools, sources, rounds, and volumes a request needs; the graph executes the plan deterministically.
- **Real, permitted sources only** — every outbound request is checked against an explicit domain allow-list, robots.txt, and per-domain token-bucket rate limits.
- **Deterministic processing** — schema-driven normalization (currency/date/URL/text) and validation in pure Python. Invalid records are flagged, never silently dropped or invented.
- **Provenance on every record** — source URL, source name, and retrieval timestamp are captured from actual HTTP responses.
- **Queryable datasets** — server-side keyword search, typed filters (`field:op:value`), multi-column sorting, pagination, JSON and streaming CSV.
- **Task lifecycle** — SSE progress events, cancellation, re-runs with versioned parent/child task history, and dataset diffing between two runs.

---

## Architecture

```text
              ┌──────────────────────────────────────────────┐
              │                Next.js Frontend              │
              │   App Router · React 19 · Tailwind CSS 4     │
              └──────────────────┬───────────────────────────┘
                                 │  REST (Bearer token)
              ┌──────────────────▼───────────────────────────┐
              │               FastAPI Backend                │
              │  routes → services → schemas → db            │
              ├──────────────────────────────────────────────┤
              │  Chat service        Collection workflow     │
              │  (OpenAI-compatible  (LangGraph: analyze →   │
              │   API + Gemini       plan → collect → clean) │
              │   grounding)                                 │
              ├──────────────────────────────────────────────┤
              │  Source policy: allow-list · robots.txt ·    │
              │  token-bucket rate limits · httpx + BS4      │
              └──────────────────┬───────────────────────────┘
                                 │  psycopg (pooled)
              ┌──────────────────▼───────────────────────────┐
              │          PostgreSQL (Supabase)               │
              │  users · sessions · conversations · messages │
              │  documents · collection_tasks · events       │
              └──────────────────────────────────────────────┘
```

- **Frontend** — Next.js App Router pages for landing, auth, the chat workspace, and settings. Client state lives in React hooks and context; all API access goes through a typed fetch wrapper that handles auth headers and error normalization.
- **Backend** — FastAPI with a strict layering: route handlers validate at the Pydantic boundary, services own business logic and persistence, and nothing leaks another user's data (every query is owner-scoped).
- **AI layer** — one OpenAI-compatible HTTP client serves both chat and collection requirement analysis. Gemini endpoints get native Google Search grounding. All LLM output is re-validated before use; anything invalid falls back to deterministic logic.
- **Collection pipeline** — a compiled LangGraph state machine. AI decides *what* to collect; application code decides *how* and enforces every access policy.
- **Database** — PostgreSQL via `psycopg` connection pool against Supabase's pooler. Idempotent SQL migrations run on startup.

## Technology Stack

| Layer | Technology | Purpose |
| --- | --- | --- |
| Frontend | Next.js 16, React 19, TypeScript, Tailwind CSS 4, Lucide | Workspace UI |
| Backend | Python, FastAPI, Pydantic v2 | API, validation, business logic |
| Workflow | LangGraph | Collection state machine |
| Collection | httpx, BeautifulSoup4 | Policy-enforced fetching and HTML extraction |
| Database | PostgreSQL (psycopg 3, connection pool) on Supabase | Persistence |
| AI | Any OpenAI-compatible chat API (OpenAI, Gemini, …) | Chat responses and requirement analysis |
| Deployment | Vercel (frontend + backend), Supabase (database) | Hosting |

## Project Structure

```text
VaultPulse.AI/
├── frontend/                  # Next.js workspace UI
│   ├── app/                   # Routes: /, /login, /register, /chat/[id], /settings
│   ├── components/            # auth/, chat/, layout/, ui/, providers/
│   ├── hooks/                 # useAuth, useChat, useConversation
│   ├── context/               # Auth + theme context
│   ├── lib/                   # Typed API clients (auth, chat, upload)
│   └── types/                 # Shared TypeScript types
│
├── backend/                   # FastAPI project
│   ├── app/
│   │   ├── routes/            # auth, conversations, chat, upload, collections
│   │   ├── services/          # business logic per domain
│   │   ├── ai/                # LangGraph graph, planner, requirement analyzers
│   │   ├── tools/             # source policy, fetcher, source adapters, registry
│   │   ├── processing/        # normalization, validation, deduplication
│   │   ├── workflow/          # executor: runs the graph, streams SSE events
│   │   ├── schemas/           # Pydantic request/response contracts
│   │   └── db.py              # psycopg pool + startup migrations
│   ├── migrations/            # Idempotent SQL migrations
│   ├── tests/                 # Pytest suite (pipeline, quality, APIs)
│   ├── api/index.py           # Vercel entrypoint
│   └── requirements.txt
│
├── docs/screenshots/          # Product screenshots
└── README.md
```

---

## Screenshots

<p align="center">
  <img src="docs/screenshots/register.png" alt="VaultPulse.AI account registration" width="800" />
</p>
<p align="center">
  <sub>Account creation — the gateway to the workspace.</sub>
</p>

<!-- TODO(team): capture and add these authenticated screenshots from the live app
     (register a demo account, then screenshot at 1440x900):
  - docs/screenshots/chat-workspace.png  — /chat/new with sidebar conversation history
  - docs/screenshots/chat-response.png   — a real provider response in a conversation
  - docs/screenshots/document-upload.png — a completed upload listed in the sidebar
  - docs/screenshots/settings.png        — /settings appearance + chat preferences
-->

---

## Getting Started

### Prerequisites

- Node.js 18+ and npm
- Python 3.11+
- A PostgreSQL database (local, or a free Supabase project)
- An API key for any OpenAI-compatible chat provider (optional — the app degrades gracefully without one)

### Clone

```bash
git clone https://github.com/Shivam-web-oss/VaultPulse.AI.git
cd VaultPulse.AI
```

### Backend

```bash
cd backend
python -m venv venv
source venv/Scripts/activate        # Windows (Git Bash); use venv/bin/activate on macOS/Linux
pip install -r requirements.txt
cp .env.example .env                # then fill in the values below
uvicorn app.main:app --reload       # API at http://localhost:8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev                         # UI at http://localhost:3000
```

The frontend talks to `http://localhost:8000` by default. Point it elsewhere with `NEXT_PUBLIC_API_URL` in `frontend/.env.local`.

### Environment Variables

`backend/.env` — copy from `.env.example`:

```env
# PostgreSQL connection string. On Vercel + Supabase, use the IPv4-compatible
# pooler host (aws-*.pooler.supabase.com, port 6543), not db.*.supabase.co.
DATABASE_URL=postgresql://user:password@host:6543/postgres?sslmode=require

# OpenAI-compatible chat endpoint. AI_PROVIDER must be "openai" or
# "openai-compatible" for LLM-based collection requirement analysis.
AI_PROVIDER=openai
AI_PROVIDER_API_KEY=
AI_PROVIDER_BASE_URL=https://api.openai.com/v1/chat/completions
AI_MODEL=gpt-4o-mini

# Comma-separated origins allowed by CORS
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

# Optional
APP_TIMEZONE=Asia/Kolkata          # timezone injected into chat system prompts
AI_LIVE_SEARCH_ENABLED=true        # Gemini Google Search grounding toggle
COLLECTOR_USER_AGENT=VaultPulse-Collector/1.0 (+https://vaultpulse.ai/bot)
LOG_LEVEL=INFO
```

`frontend/.env.local`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Tests

```bash
cd backend
pytest
```

The suite covers the graph pipeline end-to-end (real normalization/validation), currency and date parsing, quality checks, and the conversation/collection APIs.

---

## API Overview

Base URL: `http://localhost:8000`. All routes except `/health`, `/api/auth/register`, and `/api/auth/login` require `Authorization: Bearer <token>`.

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `/health` | Liveness check |
| POST | `/api/auth/register` | Create an account, returns bearer token |
| POST | `/api/auth/login` | Authenticate, returns bearer token |
| GET / POST | `/api/conversations` | List / create conversations |
| GET / PATCH / DELETE | `/api/conversations/{id}` | Open (with messages) / rename / delete |
| POST | `/api/chat/{id}/messages` | Send a message, get assistant reply |
| POST | `/api/chat/{id}/stream` | Same, as SSE chunks |
| POST | `/api/upload` | Upload PDF/DOCX/TXT/CSV (≤ 10 MB), index text |
| POST | `/api/v1/collections` | Start a collection task from a prompt |
| GET | `/api/v1/collections/{id}` | Task status |
| GET | `/api/v1/collections/{id}/result` | Full dataset, schema, provenance, quality summary |
| GET | `/api/v1/collections/{id}/data` | Search / filter / sort / paginate records; `?format=csv` |
| GET | `/api/v1/collections/{id}/events` | SSE progress stream |
| POST | `/api/v1/collections/{id}/rerun` | New versioned run of the same (or edited) prompt |
| GET | `/api/v1/collections/{id}/history` | Version chain with per-version quality stats |
| GET | `/api/v1/collections/{id}/diff/{other}` | Added / removed / changed records between runs |
| GET | `/api/v1/collections/{id}/export` | Download dataset as JSON or CSV |
| POST | `/api/v1/collections/{id}/cancel` | Cancel a running task |

### Example: start a collection

```bash
curl -X POST http://localhost:8000/api/v1/collections \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "find 20 backpacks under 50"}'
```

```json
{
  "taskId": "6f1e...",
  "status": "created",
  "parentTaskId": null,
  "version": 1
}
```

### Example: query the resulting records

```bash
curl "http://localhost:8000/api/v1/collections/$TASK_ID/data?search=backpack&filter=price:lte:50&sort=-rating&page=1&page_size=5" \
  -H "Authorization: Bearer $TOKEN"
```

```json
{
  "total": 20,
  "page": 1,
  "page_size": 5,
  "items": [
    {
      "name": "Example Backpack",
      "price": 34.95,
      "price_currency": "GBP",
      "rating": 4.0,
      "url": "https://books.toscrape.com/catalogue/example_1000/index.html",
      "source_url": "https://books.toscrape.com/catalogue/example_1000/index.html",
      "fetched_at": "2026-09-29T18:04:11.284125+00:00"
    }
  ]
}
```

*(Record shown is illustrative; the shape matches the real response.)*

---

## Example Walkthrough

**Input**

```text
Find 20 backpacks under 50
```

**What actually happens**

1. The **requirement analyzer** runs. With an AI provider configured, an LLM proposes `{entity: "product", count: 20, constraints: {maxPrice: 50}, fields: [name, price, rating, image, seller, url]}`; every field type is re-validated against a whitelist. Without a provider, a deterministic regex analyzer produces the same structure from keyword patterns.
2. The **planner** over-fetches: 40 raw records spread across up to 8 rounds against the permitted source for products, respecting per-round capacity caps.
3. The **graph loop** runs `search → extract → normalize → validate → deduplicate` per round. Prices parse into floats with ISO currency codes; records failing `maxPrice` are flagged invalid; duplicates are removed by canonical URL, then by name+seller identity.
4. The executor caps delivery at exactly 20 records and marks the task **COMPLETED** — or **PARTIAL** if sources ran dry first. Provenance entries are matched back to records by URL.

**Output structure**

```json
{
  "request": { "prompt": "Find 20 backpacks under 50" },
  "schema": { "name": "product", "fields": [ ... ] },
  "data": { "count": 20, "items": [ ... ] },
  "provenance": { "retrievedAt": "...", "entries": [ { "recordIndex": 0, "sourceUrl": "...", "sourceName": "Books To Scrape (sandbox)", "retrievedAt": "..." } ] },
  "quality": { "total_records": 20, "valid_records": 20, "percent_complete": 100.0 }
}
```

---

## The AI Layer — What It Does and Doesn't Do

AI is used in exactly two places, and both are re-validated before anything downstream trusts them:

1. **Chat responses** — the provider generates the assistant reply. When the endpoint is Gemini, native Google Search grounding can be enabled, and returned source links are appended to the answer. Without a configured provider, chat returns `503` — the backend never fabricates a response.
2. **Requirement analysis** — an LLM converts the prompt into a structured requirement and may invent *any* entity with a 1–8 field schema. Output is validated against a strict Pydantic model (field-type whitelist, count ceiling, mandatory `url` link field); any failure falls back to a deterministic regex analyzer, so the pipeline always produces a usable requirement.

Everything else is deterministic:

- Workflow planning, tool selection, and execution are plain code driven by a registered-tool allow-list. The LLM never picks arbitrary domains or bypasses policy.
- Normalization, validation, deduplication, querying, and provenance matching are pure Python.
- Search terms sent to source APIs are always derived deterministically from the raw prompt, so they can never disagree with the interpreted requirement.

This is a deliberate split: the model handles ambiguity in *what the user wants*; code guarantees *how it can happen and what quality means*.

## Data Processing

```text
Raw records (from permitted sources)
   ↓
Normalization        currency → float + ISO code (₹, Cr, Lakh, $1,200.50, €3.4M…)
                     dates → ISO 8601 with day-first rule for ambiguous formats
                     URLs → lowercase host, tracking params stripped
                     text → Unicode NFC, zero-width/control chars removed
   ↓
Validation           schema-driven type checks, required fields, maxPrice constraints
                     issues are flagged on the record (_issues, _is_valid), not deleted
   ↓
Deduplication        canonical URL first, then name+seller identity
   ↓
Structured records   provenance matched per record (source URL, name, retrieval time)
```

Summary metrics (valid/invalid counts, issues per rule, completeness %) are computed per run and exposed on the result and history endpoints.

## Data Sources and Policy

Collection only ever touches an explicit allow-list. Adding a domain requires verifying its robots.txt and terms first.

| Domain | Entity | Kind | Rate limit |
| --- | --- | --- | --- |
| `books.toscrape.com` | product | scraping sandbox (static HTML) | 1 req / 2 s |
| `www.arbeitnow.com` | job | keyless public job-board API | 1 req / 2 s |
| `hn.algolia.com` | record | official HN Search API | 1 req / s |

Every fetch goes through one policy-enforced client that: refuses non-allow-listed domains, fetches and caches robots.txt (1 h TTL — a 403 robots response blocks the whole domain), waits on a per-domain token bucket, and stamps results with the actual retrieval time. No browser automation is included; all permitted sources are static HTML or JSON APIs.

---

## Deployment

```text
Frontend   →  Vercel (Next.js)            vault-pulse-ai.vercel.app
Backend    →  Vercel (FastAPI via api/index.py)
Database   →  Supabase Postgres (pooled connection, sslmode=require)
```

- The backend applies its idempotent SQL migrations on startup and uses a bounded `psycopg` connection pool.
- `DATABASE_URL` must point at Supabase's IPv4-compatible pooler host (`aws-*.pooler.supabase.com`), since the direct `db.*` host may resolve IPv6-only.
- Deploy the backend first, set `NEXT_PUBLIC_API_URL` on the frontend project to the backend URL, then deploy the frontend. Secrets never go in `NEXT_PUBLIC_*` variables.

## Honest Status

We'd rather list this than let you discover it.

**Implemented and deployed**

- Chat workspace: accounts, persistent conversations, provider-backed replies (with Gemini grounding), document upload + text extraction, preferences, full loading/error/retry states.
- Collection API: full pipeline (analyze → plan → collect → normalize → validate → dedupe), provenance, SSE events, cancellation, versioned re-runs + history + diff, server-side query/filter/sort/pagination, JSON/CSV export.

**Implemented, API-only (no UI yet)**

- Everything under `/api/v1/collections/*`. There is currently no dashboard, task view, dataset table, or export UI in the frontend — the collection engine is usable through the API and `curl`/Postman today. A UI for it is the next major piece.

**Partial / known limitations**

- `open_pages` in the graph is a placeholder; there is no browser automation (all current sources are static HTML or JSON APIs).
- Collection tasks run as in-process daemon threads with SSE polling. That's fine locally, but it is not a durable job queue — long-running collection on serverless Vercel functions needs a queue before it's production-reliable.
- Document retrieval is keyword matching (`ILIKE`), not vector search; images upload but are not OCR'd.
- Chat "streaming" yields the completed response in line chunks, not provider token streaming.
- Sessions are database-backed opaque tokens with no expiry or logout endpoint yet.
- Collection is limited to the three sources above; arbitrary schemas don't create arbitrary collectors.

## Future Scope

- Collection dashboard: task creation, live SSE progress, dataset tables, filters, and export in the UI
- More source adapters (each verified for robots and terms) and richer per-entity extractors
- A durable job queue so long-running collections survive serverless constraints
- Vector-based document retrieval and OCR for image uploads
- True token-level chat streaming
- Scheduled re-runs with dataset diffing surfaced as change feeds
- Session expiry, logout, and refresh tokens; role-based access for shared workspaces
- Workflow versioning and observability (per-node timing, retry metrics)

## Team

Built by **shivam**, **ayushsonone07**, and **Ace Art** for a hackathon.

---

<div align="center">
  <sub><a href="https://vault-pulse-ai.vercel.app/">Try the live app</a> · <a href="#getting-started">Run it locally</a> · <a href="#honest-status">Honest status</a></sub>
</div>
