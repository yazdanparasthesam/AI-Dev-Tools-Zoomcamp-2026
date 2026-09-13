# Homework 2 — Answers (TableTurn)

Submission: https://courses.datatalks.club/ai-dev-tools-2026/homework/hw2
Deadline: 15 September 2026 (Tue), 02:30 (Asia/Tehran)

---

## Q1. Which project did you choose? (not graded)

**Restaurant waitlist manager**

## Q2. What is the name you chose? (1 point)

```
TableTurn
```

## Q3. What is the sha1 hash for this commit? (1 point)

You must generate this yourself — the hash depends on your git identity, your
files' contents, and the commit timestamp. Run this from the repo root after
copying the project in:

```bash
git add _docs/specs.md .gitignore README.md AGENTS.md
git commit -m "Add product spec, README, AGENTS.md and .gitignore"
git push
git rev-parse HEAD          # <- this is the answer for Q3
```

Paste the full 40-character hash. (A short hash usually scores too, but the
question says sha1, so give the full one.)

If you prefer to commit the whole project at once instead, the hash of that
commit is also a valid answer — but the question describes the spec commit, so
committing those four files first is the safest reading.

## Q4. Which command do you use to start the frontend? (1 point)

```
cd frontend && npm run dev
```

Alternatives that are equally correct for this repo:
- `npm run dev` (already inside `frontend/`)
- `make run-frontend` (from the repo root)

Serves http://localhost:5173

## Q5. Which command do you use to start the backend? (1 point)

```
uv run uvicorn backend.app.main:app --reload --port 8000
```

Run from the repository root. Alternatives:
- `make run-backend`
- `uv run uvicorn backend.app.main:create_app --factory --reload --port 8000`

Serves http://localhost:8000 (docs at /docs)

## Q6. Which URL does the frontend use to talk to the backend? (1 point)

```
http://localhost:8000
```

Defined once in `frontend/src/api/client.ts` as `DEFAULT_API_URL`, overridable
with `VITE_API_URL` in `frontend/.env.local`. The same URL is declared as the
server in `openapi.yaml`.

## Q7. Which command do you use for running tests? (1 point)

Backend + OpenAPI contract tests (from the repo root):

```
uv run pytest
```

Frontend tests:

```
cd frontend && npm run test
```

Both at once:

```
make test
```

Current status: 66 backend tests pass, 32 frontend tests pass.

---

## Other submission fields

**Homework URL** — your GitHub repo, e.g.
`https://github.com/<you>/tableturn` (or the folder inside your Homework 1 repo).

**Learning in public links (optional, up to 7)** — LinkedIn/X post with a 30–90 s
demo video. Draft post:

> 🚀 Week 2 of AI Dev Tools Zoomcamp by @DataTalksClub complete!
>
> Built **TableTurn**, a restaurant waitlist manager, with an AI coding agent —
> spec first, then a frontend prototype with a mocked backend, an OpenAPI
> contract, a FastAPI backend, and finally SQLite behind SQLAlchemy.
>
> Today I learned how to:
> ✅ Turn a product spec into numbered, testable business rules
> ✅ Use openapi.yaml as the source of truth — with a contract test that fails on drift
> ✅ Keep all domain rules in one store so routes stay thin
> ✅ Swap a mock database for SQLite without rewriting anything
> ✅ Catch AI mistakes by *running* the code, not reading it
>
> Repo: <LINK>
> Demo: <VIDEO_LINK>

**Reflection question** (0 points, free form) — draft:

> The most practical idea was writing the spec's business rules as numbered
> items (R1–R10) and then citing those numbers in both the tests and the code
> comments. When a test failed I could point at the exact rule it was checking,
> and when the AI generated something plausible but wrong — like a test
> asserting an average wait of 5 minutes when the correct value was 25 — the
> rule made it obvious which side was mistaken. Treating openapi.yaml as a
> contract enforced by a test, rather than documentation nobody reads, was the
> other habit I'll keep.

---

## Before you submit — checklist

- [ ] `uv sync` then `uv run pytest` → 66 passed
- [ ] `cd frontend && npm install && npm run test` → 32 passed
- [ ] Backend starts, frontend starts, UI shows seeded demo data
- [ ] Add a party → seat it → turn the table → stats update
- [ ] Refresh the browser → data still there (SQLite persistence)
- [ ] **Delete `frontend/.env.local`** if you copied the folder rather than
      cloning: it points at a sandbox preview URL that will not exist for you.
      Without it the frontend correctly defaults to `http://localhost:8000`.
- [ ] `tableturn.db` is gitignored; commit `uv.lock` and
      `frontend/package-lock.json` (they make installs reproducible)
