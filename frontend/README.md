# VaultPulse.AI

VaultPulse.AI is a secure, responsive workspace for chatting with an assistant and searching the full text of uploaded documents, growing into an AI-powered data intelligence platform that turns natural-language requests into verified structured datasets. The project has a Next.js frontend and a FastAPI backend. Authentication is shared through React Context, while the API enforces bearer authentication and user-owned data access.

## Run Locally

### Backend

```powershell
cd backend
.\venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The API runs at `http://localhost:8000`.

### Frontend

```powershell
cd frontend
npm install
npm run dev
```

The app runs at `http://localhost:3000`.

## Branding

The shield-and-pulse mark is stored in `public/vaultpulse-mark.svg` and reused through `components/BrandMark.tsx` across the landing page, authentication screens, and chat navigation. `app/icon.svg` uses the same mark as the browser icon.

Set `NEXT_PUBLIC_API_URL` in `.env.local` when the backend is not running at `http://localhost:8000`. Use `.env.example` as the template. Never commit secrets.

## Deploy To Vercel

Create a Vercel project from this repository with the project root set to `frontend`. Vercel detects Next.js automatically. Add this production environment variable before deploying:

```text
NEXT_PUBLIC_API_URL=https://your-backend-domain.example.com
```

The backend URL must include the scheme, must not end with `/`, and must allow the deployed frontend origin in its `CORS_ORIGINS` setting.

## Routing

All frontend route constants are defined in `routes/index.ts`.

| Route | Access | Purpose |
| --- | --- | --- |
| `/` | Redirect | Sends the user to the default conversation. |
| `/login` | Public | Signs in through the backend. |
| `/register` | Public | Creates an account through the backend. |
| `/chat/[conversationId]` | Protected | Lists conversations, uploads files, searches document content, and sends messages. |
| `/settings` | Protected | Stores workspace preferences locally. |

`ProtectedRoute` redirects unauthenticated users to `/login`. `AuthProvider` reads the session from browser storage and listens for logout or expired-token events. This is a client-side navigation guard; the FastAPI bearer dependency is the server-side security boundary.

## Backend API

Public endpoints:

| Method | Endpoint | Body | Purpose |
| --- | --- | --- | --- |
| `GET` | `/health` | None | Health check. |
| `POST` | `/api/auth/register` | `{ name, email, password }` | Creates a user and returns a bearer token. |
| `POST` | `/api/auth/login` | `{ email, password }` | Authenticates a user and returns a bearer token. |

Protected endpoints require `Authorization: Bearer <access_token>`:

| Method | Endpoint | Body | Purpose |
| --- | --- | --- | --- |
| `GET` | `/api/conversations` | None | Lists conversations owned by the current user. |
| `POST` | `/api/conversations` | `{ title? }` | Creates a conversation for the current user. |
| `GET` | `/api/conversations/{id}` | None | Gets one owned conversation with messages. |
| `PATCH` | `/api/conversations/{id}` | `{ title }` | Renames an owned conversation. |
| `DELETE` | `/api/conversations/{id}` | None | Deletes an owned conversation. |
| `POST` | `/api/chat/{id}/messages` | `{ message }` | Searches the user's indexed documents and returns an assistant message. |
| `POST` | `/api/chat/{id}/stream` | `{ message }` | Streams an assistant response as server-sent events. |
| `POST` | `/api/upload` | Multipart `file` | Extracts and indexes TXT, CSV, DOCX, and PDF content for the current user. |
| `POST` | `/api/v1/collections` | `{ prompt }` | Creates a data collection task and starts the pipeline in a background thread. Returns `{ taskId, status: "CREATED" }`. |
| `GET` | `/api/v1/collections/{taskId}` | None | Gets task status, prompt, and record count. |
| `GET` | `/api/v1/collections/{taskId}/result` | None | Gets the full dataset response: request, dataset, UI metadata, provenance, files. |
| `GET` | `/api/v1/collections/{taskId}/events` | None | Server-sent events stream of live pipeline progress (`PLANNING`, `SEARCHING`, `RECORDS_FOUND`, `VALIDATING`, `DEDUPLICATING`, `COMPLETED`/`PARTIAL`). |
| `GET` | `/api/v1/collections/{taskId}/export?format=json` | None | Downloads the `dataset.json` artifact (other formats return 400 for now). |
| `GET` | `/api/v1/collections/{taskId}/ui` | None | Downloads the generated `ui.html` artifact (404 until Phase F). |
| `POST` | `/api/v1/collections/{taskId}/cancel` | None | Cancels a task; rejected for terminal states (`COMPLETED`, `FAILED`, `CANCELLED`). |

Uploads are limited to 10 MB. Supported extensions are `pdf`, `docx`, `txt`, `csv`, `png`, `jpg`, and `jpeg`; text extraction is available for PDF, DOCX, TXT, and CSV. Image uploads are accepted and stored as metadata, but OCR is not enabled yet.

## Backend Structure (pipeline modules)

```text
backend/app/
├── ai/state.py                  CollectionState TypedDict with append reducers (Phase C)
├── ai/graph.py                  LangGraph StateGraph: 12 nodes + conditional loop (Phase C)
├── ai/planner.py                Requirement → multi-round source/tool plan (Phase C)
├── ai/requirement_analyzer.py   Prompt → entity, count, constraints, schema (Phase B)
├── ai/fake_collector.py         Deterministic record generation, no network (Phase B)
├── tools/registry.py            WebSearchTool / PageExtractionTool / HttpFetchTool (Phase C)
├── tools/source_policy.py       Permitted-source allowlist (Phase C)
├── processing/quality.py        Deterministic validation + deduplication (§14)
└── workflow/executor.py         Runs the graph per task, emits SSE events per node
```

## AI Data Intelligence Platform

A prompt-driven pipeline converts a natural-language requirement into a fresh, verified, structured dataset (`dataset.json`, the source of truth) and an AI-generated HTML UI for it. Two AI responsibilities are kept separate: a LangGraph workflow owns data collection/quality (implemented as a `StateGraph` in `app/ai/graph.py`: analyzer → planner → tool selector → source selection → search → pages → extract → normalize → validate → dedupe, looping back to search until the target count is met or sources are exhausted), and a UI-specialized model owns presentation only. Records are never fabricated — if sources run out, the task ends `PARTIAL`. UI generation failure never fails the task; the React fallback renders the dataset.

Task lifecycle:

```text
CREATED → RUNNING → COMPLETED | PARTIAL | FAILED
                \→ CANCELLED (from any non-terminal state)
```

Phase progress (update this table whenever a phase is implemented):

| Phase | Scope | Status |
| --- | --- | --- |
| A — Contracts | FastAPI task lifecycle, Pydantic dataset contracts, `/api/v1/collections` endpoints, `runtime/tasks/<taskId>/` artifacts | ✅ Done |
| B — Fake pipeline | Requirement analyzer, fake collector, schema + records into `dataset.json`, `COMPLETED`/`PARTIAL` transitions, SSE progress events, background executor | ✅ Done |
| C — LangGraph | `CollectionState` graph (§11), workflow planner, tool registry with source policy, conditional collection loop with exhausted→`PARTIAL` path | ✅ Done |
| D — Real collection | Web search, browser navigation, extraction tools | ⬜ Not started |
| E — Data quality | Normalization, validation, deduplication, provenance | ⬜ Not started |
| F — UI generation | UI-specialized model produces `ui.html` from dataset + schema | ⬜ Not started |
| G — UI safety | Artifact validation, sandboxing, React fallback renderer | ⬜ Not started |
| H — React panel | Prompt input, progress UI, generated-UI container, filters, export | ⬜ Not started |

## Frontend Structure

```text
frontend/
├── app/
│   ├── layout.tsx                 Root metadata and AppProvider
│   ├── page.tsx                   Default redirect
│   ├── globals.css                Global styles
│   ├── login/page.tsx             Public login route
│   ├── register/page.tsx          Public registration route
│   ├── chat/[conversationId]/    Protected chat route
│   └── settings/page.tsx          Protected settings route
├── components/
│   ├── auth/                      Login, registration, and route guard
│   ├── chat/                      Chat header, messages, composer, upload UI
│   ├── layout/                    Responsive VaultPulse.AI sidebar
│   ├── providers/                 AppProvider
│   └── ui/                        Shared UI primitives
├── context/AuthContext.tsx        Shared authenticated session state
├── hooks/
│   ├── useAuth.ts                 Login and registration actions
│   ├── useChat.ts                 Message sending and optimistic updates
│   └── useConversation.ts          Conversation loading and creation
├── lib/
│   ├── api.ts                     Authenticated fetch wrapper and 401 handling
│   ├── authApi.ts                 Auth endpoints
│   ├── chatApi.ts                 Chat and conversation endpoints
│   └── uploadApi.ts               Multipart upload endpoint
├── routes/index.ts                Central route registry
├── types/                         API, chat, conversation, and user contracts
└── utils/                         Formatting helpers
```

## Backend Structure

```text
backend/
├── app/main.py                    FastAPI application and CORS
├── app/dependencies/auth.py      Bearer-token dependency
├── app/routes/                    HTTP route modules
├── app/routes/collections.py     /api/v1/collections task endpoints (Phase A)
├── app/schemas/                   Pydantic request and response models
├── app/schemas/collection.py     Dataset contract, task status enum (Phase A)
├── app/services/auth_service.py  Password hashing and token sessions
├── app/services/conversation_service.py
├── app/services/collection_service.py  In-memory task store + runtime artifacts (Phase A)
├── app/services/document_service.py  Per-user document extraction/index
└── app/services/chat_service.py  Assistant provider boundary

runtime/                           Task artifacts, gitignored (Phase A)
└── tasks/<taskId>/
    ├── dataset.json               Dataset source of truth, written on task creation
    └── ui.html                    Generated UI artifact (arrives in Phase F)
```

## State And Data Flow

1. Login or registration calls the backend and receives `user` plus `access_token`.
2. `AuthContext` stores that session and exposes it to the entire frontend.
3. `lib/api.ts` reads the access token for every request and sends the bearer header.
4. A 401 clears the session and causes `ProtectedRoute` to send the user back to login.
5. `useConversation` loads only conversations returned for the authenticated user.
6. `useChat` sends messages and updates the shared conversation state optimistically.
7. Uploads are indexed under the authenticated user. Chat searches that user's full extracted document content before producing a response.

## Current Limitations

The chat provider is currently unconfigured and returns an explicit error instead of fabricated assistant content. User accounts, tokens, conversations, document indexes, and collection tasks are currently held in process memory, so restarting FastAPI clears them (the `runtime/tasks/<taskId>/` artifact files remain on disk). Use a database and durable token/session store before production deployment. The collection pipeline runs on LangGraph but still uses the deterministic fake collector and fake sources for development (real web collection arrives in Phase D). The fake source pool caps at 50 records, so requests above that end `PARTIAL` by design. Collection tasks and their event logs are held in process memory.

## Frontend Rules And Change Log

The frontend is maintained as a separate project from `backend/`; project-specific workflow rules are in `codex.md`. Dashboard and chat screens render backend data or explicit loading, empty, and error states. They do not create mock conversations or fabricated assistant replies. API responses and conversation/message transitions log safe metadata such as paths, statuses, IDs, and counts; credentials, file contents, and full messages are never logged.

### 2026-09-27

| Change | Reason | Effected files |
| --- | --- | --- |
| Removed the local mock conversation and default `local-new` route. | Dashboard data must come from the backend. | `lib/conversationApi.ts`, `hooks/useConversation.ts`, `routes/index.ts` |
| Replaced fabricated send-error messages with a visible error state. | Users must be able to distinguish unavailable data from an assistant response. | `hooks/useChat.ts`, `app/chat/[conversationId]/page.tsx` |
| Display backend provider-unavailable errors instead of fabricated assistant content. | The dashboard must never present mock data as a real response. | `hooks/useChat.ts`, `app/chat/[conversationId]/page.tsx` |
| Added safe API and state-transition logs. | Make data loading, creation, and message updates diagnosable. | `lib/api.ts`, `hooks/useConversation.ts`, `hooks/useChat.ts` |
| Grouped conversations by their actual update date. | Prevent the same conversation from appearing in every sidebar section. | `components/layout/Sidebar.tsx` |
| Displayed backend provider errors in the chat error state. | Make a `503` actionable instead of hiding its cause. | `hooks/useChat.ts` |

## Validation

```powershell
cd frontend
npm run lint
npm run build

cd ../backend
.\venv\Scripts\python.exe -m compileall app
```
