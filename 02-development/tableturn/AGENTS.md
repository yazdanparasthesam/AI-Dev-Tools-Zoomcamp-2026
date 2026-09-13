# AGENTS.md — TableTurn

Rules for AI coding agents (and humans) working in this repository.
Read this before changing any code.

## What this project is

TableTurn is a host-side restaurant waitlist manager. React + TypeScript
frontend in `frontend/`, FastAPI backend in `backend/`, SQLite through
SQLAlchemy. It is a teaching project from Module 2 of the AI Dev Tools
Zoomcamp — **clarity beats cleverness**.

## Sources of truth (in priority order)

1. `_docs/specs.md` — what the app must do. Business rules R1–R10 live there.
2. `openapi.yaml` — the API contract. **Change the contract before the code.**
3. `tests/` — the executable description of the rules above.

If a task contradicts one of these, stop and say so instead of silently
diverging.

## Hard rules

- **Never call `fetch` from a React component.** All HTTP goes through
  `frontend/src/api/client.ts`. New endpoint → add a typed function there first.
- **Never hardcode the backend URL** in a component. It comes from
  `import.meta.env.VITE_API_URL` (default `http://localhost:8000`), read once in
  `client.ts`.
- **No SQLite-specific SQL.** Models use generic SQLAlchemy types so Postgres
  works by changing `DATABASE_URL` only. No raw SQL strings in business logic.
- **Business rules belong in `backend/app/store.py`**, not in route handlers.
  Routes translate store results/exceptions into HTTP; the store never imports
  FastAPI.
- **Domain errors are raised, not returned as strings.** Raise `DomainError`
  subclasses; `backend/app/errors.py` maps them to status codes.
- **Timestamps are UTC** and serialised ISO-8601 with a `Z` suffix. Never use
  naive local time. Use the injectable `clock` in `store.py` rather than calling
  `datetime.now()` inline — tests depend on it.
- **Every new endpoint needs a test in `tests/` before or with the
  implementation**, and an entry in `openapi.yaml`.
- **Do not add dependencies** without being asked. No ORM besides SQLAlchemy,
  no state library, no UI kit, no Docker/CI (that is Module 3).

## Style

- Python 3.12+, type hints everywhere, `ruff` defaults, 4-space indent.
- Pydantic v2 schemas in `backend/app/schemas.py`, mirroring `openapi.yaml`.
- TypeScript strict mode. No `any` — if a type is unknown, model it.
- Components are function components with hooks; no classes.
- Keep functions short and named for the domain (`seatParty`, not `doAction2`).

## Commands

```bash
# backend (from repo root)
uv sync
uv run uvicorn backend.app.main:app --reload --port 8000
uv run pytest                     # all backend + contract tests
uv run pytest tests/test_parties.py -v

# frontend
cd frontend && npm install
npm run dev                       # http://localhost:5173
npm run test                      # vitest run
npm run build && npm run lint
```

## Definition of done for any change

- [ ] `_docs/specs.md` and `openapi.yaml` updated if behaviour/contract changed
- [ ] `uv run pytest` passes, `npm run test` passes, `npm run build` passes
- [ ] No new lint errors
- [ ] The change is visible in the UI or explained in the PR/commit message
- [ ] `docs/ai-usage-report.md` updated if an AI tool made a notable
      contribution or a notable mistake

## Known traps

- Seating must recompute `position` / `estimated_wait_minutes` for **all**
  remaining waiting parties (R5), not just the ones after the seated party.
- Turning a table completes the party (R6). Deleting a party does not free its
  table — refuse or free it explicitly.
- Frontend polling pauses while a modal is open; do not "fix" that, it prevents
  the host's selection from vanishing mid-action.
- Tests use an isolated in-memory/temp database. Never point tests at
  `tableturn.db`.
