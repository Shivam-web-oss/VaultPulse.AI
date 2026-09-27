# Frontend Codex

## Boundaries

- Treat `frontend/` as a separate Next.js project from `backend/`.
- Frontend code may call backend APIs through `frontend/lib/`, but must not import backend Python code or duplicate backend business rules.
- Keep frontend documentation and change notes in `frontend/README.md`.

## Data Integrity

- Dashboard and chat views must render API data or an explicit empty/error/loading state.
- Do not add mock, sample, demo, or fabricated user data to production UI paths.
- Do not use local fallback records as if they were persisted backend records.

## Diagnostics

- Log API request outcomes and meaningful state transitions in development.
- Never log passwords, bearer tokens, uploaded file contents, or full user messages.
- Errors must remain visible to the user through an error state; do not replace them with fabricated assistant responses.

## Verification

Run from `frontend/`:

```powershell
npm run lint
npm run build
```
