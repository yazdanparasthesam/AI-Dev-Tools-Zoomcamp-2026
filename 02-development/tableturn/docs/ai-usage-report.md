# AI Usage Report — TableTurn

Module 2 asks for a *controlled* workflow: the AI drafts, the human verifies.
This report records what was generated, what the AI got wrong, and how each
step was checked. It is deliberately specific — "the AI helped" is not a report.

## Tools used

| Tool | Used for |
| --- | --- |
| Arena.ai Agent Mode (Claude) | Spec drafting, OpenAPI contract, backend + frontend implementation, tests, docs |
| `uv` / `pytest` / `ruff` | Verifying the backend |
| `npm` / `vitest` / `tsc` / `eslint` | Verifying the frontend |
| `curl` | Manual integration check over real HTTP (not just in-process tests) |

## Workflow actually followed

1. **Spec before code.** `_docs/specs.md` was written first: goals, non-goals,
   domain model, ten numbered business rules (R1–R10), user stories with
   acceptance criteria. Nothing was generated until the rules were written down.
2. **Contract as source of truth.** `openapi.yaml` was written from the spec
   before either side existed, so the frontend and backend were built against
   the same document rather than against each other's assumptions.
3. **Backend tests first.** `tests/` was written against the rules, then
   `backend/app/store.py` implemented them. The rules are referenced by number
   in both the tests and the code comments (`R3`, `R5`, `R6`…), so a failing
   test points at a spec line.
4. **Frontend with a mocked backend.** All HTTP was centralised in
   `frontend/src/api/client.ts` from the start; components never call `fetch`.
   The frontend tests mock that module, so they never needed a live backend.
5. **Wiring, then real HTTP.** Verified with `curl` against a running server,
   including a CORS preflight from the Vite origin — in-process tests alone
   would not have caught a CORS misconfiguration.
6. **SQLite behind SQLAlchemy.** The store depends on a `WaitlistStore`
   protocol; `SqlAlchemyStore` is the implementation. `DATABASE_URL` is the only
   thing that changes between SQLite and Postgres.

## What the AI got right

- Turning the spec's numbered rules into tests that cite them. R3 (capacity /
  occupancy checks) and R5 (recompute every position after seating) are exactly
  the kind of thing that gets half-implemented by hand.
- Keeping the domain layer free of FastAPI imports, which is what makes the
  store testable without an HTTP server.
- The error envelope design (`{"error": {"code", "message"}}`) — machine-readable
  codes let the UI show the real reason ("Table T1 seats 2, but the party has 4
  guests") instead of "Something went wrong".

## What the AI got wrong, and how it was caught

Every one of these was found by *running* something, not by reading the code.

| # | Mistake | Caught by | Fix |
| --- | --- | --- | --- |
| 1 | Pinned `vitest@^5.0.0`, which made `npm install` crash with npm 10.8.2's arborist bug (`Cannot read properties of null (reading 'edgesOut')`) while resolving vitest's optional peer set | Running `npm install` | Pinned `vitest@^4.1.0`; install is clean on the npm that ships with Node 20 |
| 2 | Wrote a stats test asserting `average_wait_minutes == 5` when the correct value was **25** (forgot a 30-minute clock advance applied to the first party). **The implementation was right; the test was wrong.** | `uv run pytest` | Recomputed by hand, fixed the expectation and the misleading comment |
| 3 | `PartyCard` took `reason` / `onReasonChange` as props lifted into the parent, so picking a cancel reason on one row would silently change it on every row | Reviewing the prop list against the UX | Moved `reason` into local `useState` inside the card |
| 4 | `update_party` raised `PartyNotWaitingError` for a whitespace-only name — right status family, wrong meaning | Reading the error codes against the spec | Added `BlankNameError` (`422`, code `blank_name`) |
| 5 | Error extraction in `client.ts` used a union type TypeScript could not narrow (`Property 'error' does not exist on type '{ detail?: unknown }'`) | `npx tsc --noEmit` | Replaced casts with an `isRecord` type guard and a single `extractError` helper |
| 6 | Used `process.env` in `vite.config.ts` without Node types | `npx tsc --noEmit` | Added `@types/node` and `"node"` in `tsconfig.json` types |
| 7 | `_docs/specs.md` promised a `MemoryStore` mock class that was never written — a spec describing code that does not exist | Diffing the spec against the tree | Rewrote §10 to describe what was built (protocol + SQLAlchemy impl, in-memory SQLite for tests) |

### A false alarm worth recording

A `curl` smoke script appeared to fail with `KeyError: 'status'` when seating a
party. The actual cause was **rule R3 working correctly**: the script had picked
a 2-seat table for a party of 4, and the API returned
`409 {"code": "table_too_small"}`. The lesson: read the response body before
assuming the code is broken. The script was fixed to assert the rejection and
then seat at a table that fits.

## Verification status

| Check | Command | Result |
| --- | --- | --- |
| Backend + contract tests | `uv run pytest` | 66 passed |
| Frontend tests | `cd frontend && npm run test` | 32 passed |
| Python lint | `uv run ruff check .` | clean |
| TS types | `cd frontend && npx tsc --noEmit` | clean |
| Frontend lint | `cd frontend && npm run lint` | clean |
| Production build | `cd frontend && npm run build` | builds |
| Live HTTP + CORS | `curl` against `uvicorn` on :8000 | 201/200/409 as specified |

## Habits that made the difference

- **Never accept generated code without running it.** Six of the seven mistakes
  above were invisible to a read-through.
- **Distrust generated test expectations as much as generated code.** A test
  that asserts the wrong number is worse than no test, because it looks like
  proof. #2 was caught only because the failure was investigated instead of
  "fixed" by changing the implementation.
- **Keep the spec honest.** When the implementation diverged from the spec (#7),
  the spec was updated rather than left to rot — otherwise the next agent reads
  fiction.
- **Give the agent rules, not just tasks.** `AGENTS.md` exists so that "no fetch
  in components" and "no business rules in routes" survive the next prompt.
