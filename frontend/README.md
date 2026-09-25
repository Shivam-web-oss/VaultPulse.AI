# VaultPulse.AI

VaultPulse.AI is a secure, responsive workspace for chatting with an assistant and searching the full text of uploaded documents. The project has a Next.js frontend and a FastAPI backend. Authentication is shared through React Context, while the API enforces bearer authentication and user-owned data access.

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

Set `NEXT_PUBLIC_API_URL` in `.env.local` when the backend is not running at `http://localhost:8000`. Use `.env.example` as the template. Never commit secrets.

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

Uploads are limited to 10 MB. Supported extensions are `pdf`, `docx`, `txt`, `csv`, `png`, `jpg`, and `jpeg`; text extraction is available for PDF, DOCX, TXT, and CSV. Image uploads are accepted and stored as metadata, but OCR is not enabled yet.

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
├── app/schemas/                   Pydantic request and response models
├── app/services/auth_service.py  Password hashing and token sessions
├── app/services/conversation_service.py
├── app/services/document_service.py  Per-user document extraction/index
└── app/services/chat_service.py  Assistant provider boundary
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

The default chat provider is intentionally a replaceable mock service. User accounts, tokens, conversations, and document indexes are currently held in process memory, so restarting FastAPI clears them. Use a database and durable token/session store before production deployment.

## Validation

```powershell
cd frontend
npm run lint
npm run build

cd ../backend
.\venv\Scripts\python.exe -m compileall app
```
