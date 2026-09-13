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

The hash depends on your my identity, my files' contents, and the commit timestamp. Run this from the repo root after
copying the project in:

```bash
git add _docs/specs.md .gitignore README.md AGENTS.md
git commit -m "Add product spec, README, AGENTS.md and .gitignore"
git push
git rev-parse HEAD          # <- this is the answer for Q3
```

Paste the full 40-character hash. (A short hash usually scores too, but the
question says sha1, so give the full one.)



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

## Before submit — checklist

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
