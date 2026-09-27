# Backend Codex

## Boundaries

- Treat `backend/` as a separate FastAPI project from `frontend/`.
- Keep backend contracts, validation, authentication, logging, and business logic in `backend/`.
- Keep backend documentation and change notes in `backend/README.MD`.

## Data Integrity

- Validate and normalize request data at the Pydantic schema boundary.
- Reject empty or whitespace-only text, invalid enum/state values, negative counts, and inconsistent dataset metadata.
- Do not expose data belonging to another authenticated user.

## Diagnostics

- Log authenticated resource lifecycle events and state transitions with IDs, counts, and statuses.
- Never log passwords, access tokens, full prompts, full messages, or uploaded file contents.
- Raise structured HTTP errors for client-visible validation and resource failures.

## Verification

Run from `backend/`:

```powershell
.\\venv\\Scripts\\python.exe -m compileall app
```
