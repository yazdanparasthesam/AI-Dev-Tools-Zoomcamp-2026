# TableTurn

A host-side **restaurant waitlist manager**: queue walk-in parties, see who is
next and how long they will wait, seat them at a table that actually fits, turn
tables when they leave, and read end-of-shift stats.

Built for Module 2 of the [AI Dev Tools Zoomcamp](https://github.com/DataTalksClub/ai-dev-tools-zoomcamp)
— spec first, then a frontend prototype with a mocked backend, then an OpenAPI
contract, a FastAPI backend, and finally SQLite behind SQLAlchemy.

- **Spec** — [`_docs/specs.md`](_docs/specs.md)
- **API contract** — [`openapi.yaml`](openapi.yaml)
- **Agent rules** — [`AGENTS.md`](AGENTS.md)
- **AI usage report** — [`docs/ai-usage-report.md`](docs/ai-usage-report.md)
- **Frontend** — React 19 + TypeScript + Vite, in [`frontend/`](frontend)
- **Backend** — FastAPI + SQLAlchemy 2 + SQLite, in [`backend/`](backend)

---

## Prerequisites

| Tool | Version | Install |
| --- | --- | --- |
| [uv](https://docs.astral.sh/uv/) | 0.12+ | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Python | 3.12+ | managed by `uv` |
| Node.js | 20.19+ (or 22.12+) | [nodejs.org](https://nodejs.org) |

Or run the idempotent bootstrap, which installs `uv` if needed and then both
dependency sets:

```bash
./scripts/setup.sh
```

## Quickstart

Two terminals, both from the repository root.

**1. Backend** — http://localhost:8000

```bash
uv sync
uv run uvicorn backend.app.main:app --reload --port 8000
```

Interactive API docs: http://localhost:8000/docs

**2. Frontend** — http://localhost:5173

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. On the first run the backend seeds four tables and
three waiting parties so the screen is not empty.

> Nothing to click through? Try: **Seat** a party → pick a table → **Turn
> table** → watch the stats bar update.

## Running the tests

```bash
uv run pytest          # backend + contract tests   (66 tests)
cd frontend && npm run test   # frontend tests      (32 tests)
```

Or both at once:

```bash
make test
```

Other checks:

```bash
uv run ruff check .            # python lint
cd frontend && npm run lint    # eslint
cd frontend && npm run build   # typecheck + production build
```

## Commands reference

| Task | Command | Run from |
| --- | --- | --- |
| Start frontend | `npm run dev` | `frontend/` |
| Start backend | `uv run uvicorn backend.app.main:app --reload --port 8000` | repo root |
| Backend tests | `uv run pytest` | repo root |
| Frontend tests | `npm run test` | `frontend/` |
| Install Python deps | `uv sync` | repo root |
| Install Node deps | `npm install` | `frontend/` |
| Production build | `npm run build` | `frontend/` |

## How the frontend finds the backend

The frontend calls the backend directly at

```
http://localhost:8000
```

That default lives in exactly one place — `frontend/src/api/client.ts`
(`DEFAULT_API_URL`) — and can be overridden without touching code:

```bash
# frontend/.env.local
VITE_API_URL=http://localhost:8000
```

The backend allows that origin through CORS (`CORS_ORIGINS`, default
`http://localhost:5173,http://127.0.0.1:5173`). If you serve the frontend from
another port or host, add it:

```bash
CORS_ORIGINS="http://localhost:5173,https://my-preview.example.com" \
  uv run uvicorn backend.app.main:app --reload --port 8000
```

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `DATABASE_URL` | `sqlite:///./tableturn.db` | Any SQLAlchemy URL. Postgres works unchanged: `postgresql+psycopg://user:pass@localhost/tableturn` |
| `CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | Comma-separated allowed browser origins |
| `SEED_DEMO_DATA` | `true` | Seed demo tables/parties when the database is empty |
| `VITE_API_URL` | `http://localhost:8000` | Frontend → backend base URL |

Data lives in `tableturn.db` (gitignored). Delete it to start over.

## Project layout

```text
.
├── _docs/specs.md          # product spec: user stories, rules R1-R10, non-goals
├── AGENTS.md               # rules for AI agents (and humans) in this repo
├── openapi.yaml            # API contract — source of truth for both sides
├── pyproject.toml          # uv project: backend deps, pytest + ruff config
├── Makefile                # install / run / test shortcuts
├── backend/
│   └── app/
│       ├── main.py         # create_app() factory, CORS, lifespan
│       ├── api.py          # routes — HTTP translation only, no rules
│       ├── store.py        # WaitlistStore protocol + SQLAlchemy impl (the rules)
│       ├── models.py       # ORM models, database-agnostic types
│       ├── schemas.py      # Pydantic models mirroring openapi.yaml
│       ├── database.py     # engine / session plumbing
│       ├── errors.py       # DomainError hierarchy -> HTTP status codes
│       ├── config.py       # env-driven settings
│       └── seed.py         # demo data for an empty database
├── frontend/
│   └── src/
│       ├── api/client.ts   # the ONLY module that talks to the backend
│       ├── api/types.ts    # TypeScript mirror of openapi.yaml
│       ├── hooks/          # polling
│       ├── components/     # StatsBar, WaitlistPanel, FloorPanel, SeatDialog…
│       └── lib/format.ts   # display formatting
├── tests/                  # pytest: API, business rules, stats, contract
└── docs/ai-usage-report.md # what the AI wrote, what it got wrong, how it was checked
```

## The API at a glance

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/health` | liveness |
| GET/POST | `/api/parties` | list (optionally `?status=waiting`) / add |
| GET/PATCH/DELETE | `/api/parties/{id}` | read / edit / hard-delete |
| POST | `/api/parties/{id}/seat` | seat at `{table_id}` |
| POST | `/api/parties/{id}/cancel` | cancel with `{reason}` |
| GET/POST | `/api/tables` | list / add |
| PATCH/DELETE | `/api/tables/{id}` | edit / delete (free tables only) |
| POST | `/api/tables/{id}/free` | turn the table |
| GET | `/api/stats` | shift statistics |

Domain errors come back as `{"error": {"code": "table_too_small", "message": "…"}}`
with `404` / `409` / `422`, so the UI can show the real reason instead of a
generic failure.

## Business rules worth knowing

The full list is in [`_docs/specs.md`](_docs/specs.md) §6. The ones you notice
while using the app:

- **R2** — wait estimate = `(position − 1) × 10` minutes. The first party reads
  "Seating now".
- **R3** — a party can only be seated at a *free* table that is *big enough*.
  The UI disables impossible tables; the API rejects them with `409` anyway.
- **R5** — seating or cancelling recomputes every remaining position, so the
  list never has gaps.
- **R6** — turning a table moves its party to `completed`.
- **R8** — an occupied table cannot be deleted; turn it first.

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| Banner: "Backend unreachable" | The backend is not running on port 8000, or `VITE_API_URL` points somewhere else. |
| `409 table_too_small` | Pick a table whose capacity ≥ party size. |
| Port 8000 already in use | `uv run uvicorn backend.app.main:app --reload --port 8001` and set `VITE_API_URL=http://localhost:8001` in `frontend/.env.local`. |
| Vite: "Blocked request. This host is not allowed" | You are reaching the dev server through a proxy. `VITE_DEV_ALLOWED_HOSTS="*" npm run dev`. |
| Stale demo data | Delete `tableturn.db` and restart the backend. |

## Scope / non-goals

No auth, no guest-facing page, no SMS, no reservations, no multi-venue, no
WebSockets (the frontend polls every 5 s). Containers, CI and deployment are
Module 3. See [`_docs/specs.md`](_docs/specs.md) §3.
