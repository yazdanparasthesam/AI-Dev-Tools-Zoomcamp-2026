# Build Guide — TableTurn from scratch

A complete, ordered path to build this project yourself with an AI coding agent.
Written to be followed top to bottom. Each phase has: **goal → commands →
the prompt to give your agent → verification gate → exit criteria**.

The seven phases map one-to-one onto the seven homework questions.

| Phase | Homework question | Deliverable | ~Time |
| --- | --- | --- | --- |
| 0 | — | Toolchain installed | 10 min |
| 1 | Q1, Q2, **Q3** | Repo + `_docs/specs.md` + first commit | 40 min |
| 2 | — | `openapi.yaml` | 30 min |
| 3 | **Q5** | Backend, tests-first, mock store | 90 min |
| 4 | **Q4** | Frontend prototype, mocked API | 90 min |
| 5 | **Q6** | Frontend ↔ backend wired | 30 min |
| 6 | **Q7** | Mock store → SQLite/SQLAlchemy | 60 min |
| 7 | — | Docs, demo video, submission | 45 min |

Total: roughly 6–7 hours of focused work.

> **The one rule that makes this work:** never move to the next phase until the
> current phase's verification gate passes. Every mistake recorded in
> `docs/ai-usage-report.md` was caught by *running* something at a gate.

---

## Phase 0 — Toolchain

### Commands

```bash
# uv (the homework requires it for the backend)
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.local/bin/env        # or restart your shell

# verify
uv --version                       # 0.12+
node -v                            # 20.19+ or 22.12+
npm -v
git --version
```

### Verification gate

All four commands print a version. If `uv: command not found`, your `PATH`
needs `$HOME/.local/bin`.

> This repo ships `scripts/setup.sh`, which installs `uv` if missing and then
> runs `uv sync` + `npm install` idempotently. Useful after a fresh clone, or
> after anything that deletes untracked directories (`.venv` and `node_modules`
> are not committed, so a CI runner or a fresh container starts without them).

### Pitfalls

- **Node version matters.** Vite 8 needs Node `^20.19.0 || >=22.12.0`. Older
  Node fails with cryptic syntax errors, not a version message.
- **npm 10.8.x has an arborist bug** (`Cannot read properties of null (reading
  'edgesOut')`) that `vitest@5` triggers. Pin `vitest@^4.1.0`. This cost me a
  debugging cycle; you can skip it.

---

## Phase 1 — Repo + spec → **answers Q1, Q2, Q3**

### 1.1 Create the repo

```bash
# On GitHub: create an empty repo named "tableturn" (no README, no .gitignore)
git clone git@github.com:<you>/tableturn.git
cd tableturn
mkdir -p _docs docs backend/app frontend tests
```

> The homework allows a folder inside your Homework 1 repo instead. If you do
> that, every command below runs from that folder, and Q3's hash is the commit
> you make there.

### 1.2 Generate the spec with a chat assistant

The homework explicitly says to use a **chat assistant** (not a coding agent) for
this, answer its questions, then have it write the file. Prompt:

```text
I'm building a restaurant waitlist manager as a learning project. Help me write
a product spec before any code exists.

Interview me first: ask about the users, the core flow, the data model, and
what should be explicitly out of scope. Ask a few questions at a time and wait
for my answers.

Then produce a markdown spec with these sections:
1. Problem
2. Goals
3. Non-goals (be aggressive — this is a one-week project)
4. Users
5. Domain model (every field, type, and nullability)
6. Business rules — NUMBER THEM R1, R2, R3… so tests can cite them
7. User stories with Given/When/Then acceptance criteria
8. API surface (method, path, purpose, success code)
9. Frontend behaviour
10. Persistence
11. Testing strategy
12. Definition of done

Stack is fixed: React+TypeScript+Vite frontend, FastAPI backend, SQLite via
SQLAlchemy, openapi.yaml as the contract.

Also suggest 4 candidate names for the app.
```

**Why the numbered rules matter more than anything else in this phase.** R1–R10
become the vocabulary for the whole project: tests cite them, code comments cite
them, and when the agent generates something plausible-but-wrong you can point
at the rule it violates. Without numbers you get "that's not what I meant"; with
numbers you get "this breaks R5".

### 1.3 Review the spec yourself

Non-negotiable checks before you accept it:

- [ ] Are the wait-time estimate and list ordering **deterministic**? (Mine:
  `position` = 1-based index ordered by `created_at` then `id`; estimate =
  `(position − 1) × 10` minutes.) Vague rules here become flaky tests later.
- [ ] Is every status transition explicit? (`waiting → seated → completed`,
  `waiting → cancelled`.) Draw the state machine. If you can't, the agent can't.
- [ ] Does every "what if" have an answer? Table too small? Table already
  occupied? Delete a seated party? Cancel a seated party? Shrink a table under
  its occupants? **These five became R3, R6, R7, R8 in my spec.**
- [ ] Are non-goals real? Auth, SMS, reservations, multi-venue, WebSockets — all
  explicitly out. Write them down or the agent will build them.
- [ ] Are timestamps specified? (Mine: stored and returned UTC, ISO-8601 with a
  `Z` suffix → R10. This single rule prevented a genuine SQLite bug in Phase 6.)

Save to `_docs/specs.md`.

### 1.4 Write AGENTS.md

This is the file that keeps the *next* prompt from undoing the last one. Prompt:

```text
Based on _docs/specs.md, write AGENTS.md: the rules an AI coding agent must
follow in this repo. Include:
- sources of truth in priority order (spec, openapi.yaml, tests)
- hard architectural rules (where HTTP calls live, where business rules live,
  what must never be imported where)
- style rules
- the exact commands to run/test/lint
- a definition of done
- "known traps" — the mistakes an agent is likely to make here
```

Then **hand-edit it**. Mine contains rules that only exist because I hit the
problem: "no `fetch` in components", "no business rules in route handlers",
"no SQLite-specific SQL", "use the injectable clock, not `datetime.now()`".

### 1.5 .gitignore, README.md

Write `.gitignore` first (Python, Node, `*.db`, `.env*`, editor cruft) so you
never accidentally commit `node_modules`.

The README can be a stub now — you'll finish it in Phase 7.

### 1.6 Commit → **this is Q3**

```bash
git add _docs/specs.md .gitignore README.md AGENTS.md
git commit -m "Add product spec, README, AGENTS.md and .gitignore"
git push -u origin main
git rev-parse HEAD        # ← 40-char sha1 = your Q3 answer
```

### Exit criteria

`git rev-parse HEAD` prints a hash. Those four files are on GitHub. You can
state the app's name (Q2) and project (Q1).

---

## Phase 2 — The OpenAPI contract

Do this **before** either side exists. If you build the frontend first and
derive the contract from it later, you get a contract that documents accidents.

### Prompt

```text
Read _docs/specs.md. Write openapi.yaml (OpenAPI 3.1.0) at the repo root
implementing exactly the API surface in section 8.

Requirements:
- Every schema in components/schemas mirrors the domain model in section 5,
  field for field, with correct nullability.
- Computed fields (position, estimated_wait_minutes) are documented with the
  rule number that defines them.
- Define ONE error shape: {"error": {"code": string, "message": string}} as an
  ErrorEnvelope schema, referenced by every 404 and 409 response.
- Give every operation an explicit operationId in camelCase.
- Declare servers: [{url: http://localhost:8000}]
- Do not add endpoints I didn't ask for. Do not add auth.
```

### Verification gate

```bash
uv run --with pyyaml python -c "
import yaml
spec = yaml.safe_load(open('openapi.yaml'))
print(spec['openapi'], spec['info']['title'])
for path, item in spec['paths'].items():
    for method, op in item.items():
        if method in {'get','post','patch','delete'}:
            print(f'{method.upper():6} {path:38} {op.get(\"operationId\")}')
"
```

Every path from spec §8 appears, each with an `operationId`, and nothing extra.

### Design decisions worth copying

- **A single error envelope with machine-readable `code`s** (`table_too_small`,
  `party_not_waiting`, `table_occupied`) is what lets the UI say *"Table T1
  seats 2, but the party has 4 guests"* instead of *"Error"*. Decide this now;
  retrofitting it means touching every handler and every component.
- **`operationId`s in the contract** let you later generate a typed client. They
  also make the Phase 6 contract test meaningful.

---

## Phase 3 — Backend, tests first → **answers Q5**

### 3.1 Initialise the uv project

```bash
uv init --bare --name tableturn --python 3.12
uv add fastapi "uvicorn[standard]" sqlalchemy pydantic
uv add --dev pytest httpx pyyaml ruff
```

Then edit `pyproject.toml` — two settings are essential:

```toml
[tool.uv]
package = false          # backend/ is a plain package dir, not an installable dist

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]       # so `import backend.app...` and `from tests.conftest import ...` work
addopts = "-ra"
```

Without `pythonpath = ["."]` your tests fail with `ModuleNotFoundError: backend`
and you'll waste time on `conftest.py` sys.path hacks.

### 3.2 Build the skeleton (empty, but importable)

```text
backend/__init__.py
backend/app/__init__.py
backend/app/config.py     # env-driven Settings: DATABASE_URL, CORS_ORIGINS, SEED_DEMO_DATA
backend/app/errors.py     # DomainError hierarchy
backend/app/schemas.py    # Pydantic models mirroring openapi.yaml
backend/app/store.py      # WaitlistStore protocol + implementation (THE RULES)
backend/app/api.py        # routes
backend/app/main.py       # create_app() factory
backend/app/database.py   # added in Phase 6
backend/app/models.py     # added in Phase 6
backend/app/seed.py       # added in Phase 6
```

**The layering rule, stated once and enforced by AGENTS.md:**

```
api.py    → HTTP translation only. No if-statements about business state.
store.py  → every rule R1–R10. Never imports fastapi.
schemas.py→ shape only. No logic beyond serialisation.
```

This is what makes the Phase 6 database swap a non-event.

### 3.3 Write the tests BEFORE the implementation

```text
Read _docs/specs.md and openapi.yaml. Write pytest tests in tests/ for the
backend, BEFORE implementing it. One test per acceptance criterion, plus one
test per business rule R1–R10, citing the rule number in the docstring.

Provide tests/conftest.py with:
- a FakeClock class (deterministic now(), with .advance(minutes=…)) so wait-time
  and average-wait tests don't depend on wall-clock time
- a fixture that builds an isolated app per test — never a shared dev database
- helpers add_party(client, name, size) and add_table(client, name, capacity)

Use fastapi.testclient.TestClient. Assert status codes AND the error "code"
field, not just the message.
```

**The FakeClock is not optional.** Average wait (R9) and longest wait are
time-derived. Without an injectable clock those tests pass in the morning and
fail at midnight, and you'll blame the wrong thing.

Then implement:

```text
Now implement backend/app/ to make those tests pass. Rules live in store.py.
Routes must contain no business logic. Raise DomainError subclasses from the
store; map them to HTTP in errors.py via an exception handler.
Use an in-memory dict-based store for now — we swap in SQLAlchemy later.
Do not create models.py or database.py yet.
```

### 3.4 Verification gate

```bash
uv run pytest -q         # all green
uv run ruff check .      # clean
```

Then start it and hit it with curl — **in-process tests do not prove the server
runs**:

```bash
uv run uvicorn backend.app.main:app --reload --port 8000
# in another terminal:
curl -s localhost:8000/health
curl -s -X POST localhost:8000/api/parties \
  -H 'Content-Type: application/json' -d '{"name":"Ava","party_size":4}'
```

### **Q5 answer**

```
uv run uvicorn backend.app.main:app --reload --port 8000
```

### Pitfalls I hit here

- **Ruff's B008 flags every FastAPI route.** `Depends()` in an argument default
  *is* the framework's idiom. Fix in `pyproject.toml`, don't rewrite your routes:
  ```toml
  [tool.ruff.lint.flake8-bugbear]
  extend-immutable-calls = ["fastapi.Depends", "fastapi.Query", "fastapi.Path", "fastapi.Body"]
  ```
- **A wrong test expectation is worse than no test.** My stats test asserted
  `average_wait_minutes == 5`; the correct value was 25 (I'd forgotten a clock
  advance applied to the first party). The implementation was right. When a test
  fails, recompute by hand *before* touching the code.
- **Wrong error class for the case.** Blank-name handling initially raised
  `PartyNotWaitingError` — right status family, wrong meaning. Give each failure
  its own code.

### Exit criteria

`uv run pytest` green, ruff clean, curl returns real JSON, and you can name the
file where each of R1–R10 lives.

---

## Phase 4 — Frontend prototype with a mocked backend → **answers Q4**

### 4.1 Scaffold

```bash
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install

# Pin vitest to 4.x — see the Phase 0 pitfall.
npm i -D vitest@^4.1.0 jsdom @types/node
npm i -D @testing-library/react @testing-library/dom \
         @testing-library/jest-dom @testing-library/user-event
npm i -D eslint @eslint/js typescript-eslint globals
```

Delete the boilerplate (`App.css`, the counter demo, the Vite/React logos) —
leaving it in confuses the agent into styling around it.

`vite.config.ts`:

```ts
/// <reference types="vitest/config" />
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

const allowedHosts = process.env.VITE_DEV_ALLOWED_HOSTS;

export default defineConfig({
  plugins: [react()],
  server: {
    host: true,                 // bind 0.0.0.0, not just localhost
    port: 5173,
    ...(allowedHosts ? { allowedHosts: allowedHosts === "*" ? true : allowedHosts.split(",") } : {}),
  },
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: "./src/setupTests.ts",
    restoreMocks: true,
    env: { VITE_API_URL: "" },  // pin it, so a dev's .env.local can't change test assertions
  },
});
```

`tsconfig.json` needs `"types": ["vite/client", "node", "vitest/globals", "@testing-library/jest-dom"]`
— omit `"node"` and `process.env` in the config file fails typecheck.

### 4.2 Build the API layer first, mocked

This is the single most important structural decision in the frontend.

```text
Read _docs/specs.md and openapi.yaml.

Create frontend/src/api/types.ts: TypeScript interfaces mirroring every schema
in openapi.yaml, field for field, snake_case, with correct null unions.

Create frontend/src/api/client.ts: the ONLY module allowed to talk to the
backend. Export one typed function per operation, named after its operationId.
For now, implement them against an in-memory mock (a module-level array +
setTimeout) so the UI is fully usable with no backend running.

Rules:
- No component may call fetch. No component may hardcode a URL.
- Base URL comes from import.meta.env.VITE_API_URL, default
  http://localhost:8000, read exactly once.
- Export an ApiError class carrying {status, code, message} so the UI can show
  the server's real reason.
```

Then the UI:

```text
Implement the UI for _docs/specs.md section 9 using the client module.

Components: StatsBar, WaitlistPanel, AddPartyForm, PartyCard, FloorPanel,
AddTableForm, TableCard, SeatDialog, HistoryPanel, Toast.

- SeatDialog must show tables that are too small or occupied as DISABLED with
  the reason visible, not omit them (mirrors R3 in the UI).
- Poll parties/tables/stats every 5s. Pause polling while a modal is open.
- Every failed request shows a toast with the server message. No silent failures.
- Loading and empty states for every list.
- No routing library. Single screen.
```

### 4.3 Frontend tests

```text
Write vitest + React Testing Library tests:
- src/lib/format.test.ts: pure formatting functions, including edge cases
  (estimate 0, negative clock skew, null)
- src/api/client.test.ts: stub global fetch; assert the exact URL, method, JSON
  body, error-envelope parsing, 204 handling, and the network-failure path
- src/App.test.tsx: vi.mock the client module; assert list ordering, the R2
  estimates, client-side validation blocking a bad submit, that the seat dialog
  disables too-small and occupied tables, and the unreachable-backend banner
```

`vi.mock("./api/client")` is why the API layer had to be one module: the whole
UI becomes testable with no server.

### 4.4 Verification gate

```bash
npx tsc --noEmit      # types
npx eslint .          # lint
npx vitest run        # tests
npm run build         # production build
npm run dev           # click through it with the mock
```

### **Q4 answer**

```
cd frontend && npm run dev
```

### Pitfalls I hit here

- **State lifted too far.** `PartyCard` first took `reason`/`onReasonChange` as
  props from the parent — so choosing "Walked out" on one row silently changed
  every row. Per-row UI state belongs in the row.
- **TypeScript can't narrow a lazy union.** `body as ApiErrorEnvelope | {detail?: unknown}`
  then `body.error` → `TS2339`. Fix with a real type guard:
  ```ts
  function isRecord(v: unknown): v is Record<string, unknown> {
    return typeof v === "object" && v !== null;
  }
  ```
- **`getByText` matches the whole element.** My notes render as `📝 {notes}`, so
  `getByText("window seat")` fails — the element's text is `"📝 window seat"`.
  Use a regex.
- **Empty-string env vars.** `import.meta.env.VITE_API_URL ?? DEFAULT` keeps `""`
  and produces a broken base URL. Use `raw?.trim() || DEFAULT`.

### Exit criteria

The full app is clickable against the mock. All four checks pass.

---

## Phase 5 — Wire frontend to backend → **answers Q6**

### 5.1 Replace the mock with real fetch

```text
Replace the in-memory mock in frontend/src/api/client.ts with real fetch calls
against the same base URL. Keep every exported function signature identical so
no component changes.

Requirements:
- Send Content-Type: application/json
- Handle 204 (no body)
- Parse {"error":{code,message}} into ApiError; fall back to FastAPI's
  {"detail": …} for 422; fall back to the HTTP status otherwise
- Wrap fetch in try/catch and throw ApiError(0, "network_error", …) so a dead
  backend shows a banner instead of a stack trace
```

Keeping signatures identical is the payoff for Phase 4.2: **zero component
changes**.

### 5.2 Backend CORS

The browser will block the request without it. In `create_app()`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),   # default: http://localhost:5173, http://127.0.0.1:5173
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

Drive it from `CORS_ORIGINS` (comma-separated) rather than hardcoding — you'll
want a different origin for any hosted preview.

### 5.3 Verification gate — check the preflight, not just the GET

A `GET` can succeed while `POST` fails, because only non-simple requests trigger
a preflight. Test the preflight explicitly:

```bash
curl -s -i -X OPTIONS http://localhost:8000/api/parties \
  -H "Origin: http://localhost:5173" \
  -H "Access-Control-Request-Method: POST" | grep -i access-control
```

Expect `access-control-allow-origin: http://localhost:5173` and
`access-control-allow-methods` including POST. Then in the browser: add a party,
seat it, turn the table, refresh — and watch the uvicorn log for the status
codes.

### **Q6 answer**

```
http://localhost:8000
```

(Configurable via `VITE_API_URL`; declared once in `frontend/src/api/client.ts`
as `DEFAULT_API_URL` and as the `servers` entry in `openapi.yaml`.)

### Pitfall

- **"Blocked request. This host is not allowed"** — Vite rejects non-localhost
  `Host` headers. Only relevant behind a proxy/tunnel; hence the opt-in
  `VITE_DEV_ALLOWED_HOSTS` env var rather than weakening the default.

---

## Phase 6 — Mock store → SQLite via SQLAlchemy → **answers Q7**

Two valid paths:

- **(A) Homework-intended:** you built a dict-based mock in Phase 3, now you
  swap it. Follow 6.1–6.5.
- **(B) Shortcut:** go straight to SQLAlchemy behind the `WaitlistStore`
  protocol (this is what the delivered repo does). Faster, but you skip the
  lesson about the seam being real. I recommend (A) the first time.

### 6.1 Add the ORM layer

```text
Add backend/app/models.py and backend/app/database.py.

models.py: SQLAlchemy 2.x declarative models for Party and Table matching
openapi.yaml. Store UUIDs as String(36), datetimes as DateTime(timezone=True).
GENERIC TYPES ONLY — no SQLite-specific types, because Postgres must work by
changing DATABASE_URL and nothing else. Add an index on
(status, created_at, id) since that's the ordering R1 depends on.

database.py: a Database class owning engine + sessionmaker, with
expire_on_commit=False. For sqlite URLs pass check_same_thread=False, and use
StaticPool when the URL is in-memory so tests share one connection.
```

### 6.2 Rewrite the store against the protocol

```text
Replace the in-memory store with SqlAlchemyStore implementing the SAME
WaitlistStore protocol. Do not change any route or any test.

Every rule R1–R10 must still hold, and stay in store.py.

Critical: SQLite returns NAIVE datetimes (it stores no timezone) while Postgres
returns aware ones. Normalise on read:

    def ensure_utc(dt):
        if dt is None: return None
        return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)

This is what makes R10 (ISO-8601 with a Z suffix) true on both engines.
```

### 6.3 The seam that makes this safe

Because routes depend on the `WaitlistStore` **protocol**, and tests build the
app via `create_app(database_url="sqlite://", seed=False, clock=fake)`, the swap
touches one file. If you find yourself editing `api.py` here, the layering
leaked — fix the layering, don't push on.

### 6.4 Add the contract test

```text
Add tests/test_contract.py: load openapi.yaml, extract every (path, method) and
operationId, and compare against app.openapi(). Fail on drift in EITHER
direction, and on operationId mismatch.
```

This is what turns "openapi.yaml is the source of truth" from a claim into an
enforced fact.

### 6.5 Seed + persistence

Add `seed.py` (demo tables/parties, only when the DB is empty and
`SEED_DEMO_DATA=true`), and call `create_all()` from a lifespan hook. Tests pass
`seed=False`.

### 6.6 Verification gate

```bash
uv run pytest -q                      # the SAME tests, still green
uv run ruff check .
cd frontend && npx vitest run && npx tsc --noEmit

# Persistence proof — the thing the mock could never do:
uv run uvicorn backend.app.main:app --reload --port 8000
#   add a party in the browser, Ctrl-C the server, restart it, refresh
#   → the party is still there. This is SQLite, and it's worth filming.
```

### **Q7 answer**

```
uv run pytest
```

(frontend: `cd frontend && npm run test`; both: `make test`)

### Pitfalls I hit here

- **Positions are computed, never stored.** `position` and
  `estimated_wait_minutes` are derived from the ordered waiting list on every
  read. Storing them means every seat/cancel must renumber rows — a bug farm.
  R5 falls out for free if you compute.
- **Don't keep a duplicate rule implementation.** I spec'd a `MemoryStore` "for
  fast unit tests" and never wrote it, because a second implementation of R1–R10
  *will* diverge. In-memory SQLite is already fast. **I then had to correct the
  spec** — a spec describing code that doesn't exist is worse than no spec.

---

## Phase 7 — Docs, demo, submission

### 7.1 Finish README.md

It must let a stranger run the app from a clean clone. Include: prerequisites
with versions, two-terminal quickstart, **the exact commands for Q4–Q7 in a
table**, how the frontend finds the backend, an env-var table, project layout,
API summary, the business rules a user would notice, and a troubleshooting
table.

### 7.2 Write docs/ai-usage-report.md

A required deliverable, and the one most people phone in. Make it specific:

- Tools used, and the actual phase order you followed
- What the agent got **right**
- A table of what it got **wrong**, each row with: mistake → what caught it →
  fix. ("Caught by: `npx tsc --noEmit`" is evidence you verified.)
- A false alarm, and what it taught you
- Verification status: every command and its result
- The habits that made the difference

### 7.3 Makefile (optional but it makes Q7 a one-liner)

`make install / run-backend / run-frontend / test / lint / build / clean-db`.

### 7.4 Record the demo video (30–90 s)

The homework suggests exactly what to show, and it maps onto the rules:

1. Add a party → it lands at the end with a position and estimate (**R1, R2**)
2. Seat it → T1 greyed out as "Too small" (**R3**), remaining parties move up (**R5**)
3. Turn the table → party becomes Completed, average wait updates (**R6, R9**)
4. Same data in a second browser → polling (**spec §9**)
5. Refresh → data survives (**SQLite**)

### 7.5 Final checklist and submit

```bash
uv run pytest -q                    # 66 passed
cd frontend && npm run test         # 32 passed
uv run ruff check .                 # clean
cd frontend && npx eslint . && npx tsc --noEmit   # clean
cd frontend && npm run build        # builds
git status                          # no node_modules, .venv, *.db, .env.local
```

Commit `uv.lock` and `frontend/package-lock.json` — they make your install
reproducible for the grader. Then push, post your "learning in public" link, and
submit at https://courses.datatalks.club/ai-dev-tools-2026/homework/hw2 with the
answers from `homework-2-answers.md`.

---

## If you only remember five things

1. **Number your business rules in the spec** (R1…R10) and cite them in tests
   and comments. It converts arguments into lookups.
2. **Contract before code.** `openapi.yaml` first, then a test that fails on
   drift.
3. **One HTTP module, one rules module.** All `fetch` in `api/client.ts`; all
   rules in `store.py`. These two seams are why the mock→real swaps in Phases 5
   and 6 touched one file each.
4. **Inject the clock.** Any test involving wait times is flaky without it.
5. **Run it at every gate.** Six of the seven real mistakes in this project were
   invisible to a read-through and obvious to a test run.
