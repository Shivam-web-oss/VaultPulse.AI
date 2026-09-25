# AI Assistant

A separate Next.js frontend and FastAPI backend for a production-style AI chatbot interface. The first version uses in-memory conversations and a mock backend provider, so a real AI provider can be added later without changing the frontend contract.

## Run the frontend

```bash
cd frontend
npm install
npm run dev
```

Copy `frontend/.env.example` to `frontend/.env.local` when the API is not running on the default URL.

## Run the backend

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Copy `backend/.env.example` to `backend/.env` for local configuration. No API key is needed for the mock provider.

## Routes

- `/chat`: new assistant workspace
- `/chat/[conversationId]`: a specific conversation
- `/settings`: appearance and chat preferences
- `GET /health`: backend health check
- `/api/conversations`: conversation CRUD
- `/api/chat/{conversation_id}/messages`: mock assistant response
- `/api/chat/{conversation_id}/stream`: SSE-ready response stream
- `/api/upload`: PDF, DOCX, TXT, CSV, and image uploads
- `/api/auth/register`: create an account
- `/api/auth/login`: authenticate an account

Frontend API calls use `NEXT_PUBLIC_API_URL`; provider secrets belong only in the backend environment.
