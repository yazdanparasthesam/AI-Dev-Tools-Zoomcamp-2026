# Testing Agent Relay

Two suites, deliberately different in what they need and what they prove.

## 1. Starter suite — `test_agent_relay.py` (no server required)

FastAPI `TestClient` against an in-process app on throwaway SQLite
(`RELAY_DATABASE_URL` overrides the DSN; default is a local sqlite file).
Covers routing, auth tokens, lease semantics and error shapes.

```bash
uv sync
uv run pytest test_agent_relay.py -q        # 4 passed
```

## 2. Integration suite — `tests/integration/test_task_flow.py` (live server required)

SPEC.md acceptance scenario 1, executed over real HTTP against whatever
`BASE_URL` points at (default `http://127.0.0.1:8000`): the dev server, a
`docker run` container, the Compose stack, or a port-forwarded kind cluster.
The module-scoped `client` fixture **skips** when nothing answers `/health`,
so a bare `uv run pytest -q` stays green on a laptop with no server up.

```bash
uv run uvicorn main:app --reload &                 # or any other live relay
uv run pytest tests/integration -q                 # 1 passed
BASE_URL=http://127.0.0.1:8005 uv run pytest tests/integration -q   # explicit target
```

What the single test asserts, in order:

1. sender registers, worker registers;
2. `POST /api/v1/tasks` → `201`, status `queued` (and still `queued` on GET);
3. worker `POST /api/v1/tasks/claim` → gets the task, status flips `processing`;
4. worker `POST /api/v1/tasks/{id}/complete` → sender's GET shows
   **`completed`** + the exact output + `finished_at` (this is Q2);
5. `GET .../attempts` exposes delivery history but never the claim token;
6. a third, uninvolved agent gets `404` on both the task and its attempts.

## 3. In CI (`.github/workflows/ci.yml`, job `test`)

- starter suite runs on SQLite inside an `ubuntu:22.04` container;
- a `postgres:16` **service container** (healthchecked with `pg_isready`) backs
  a live uvicorn booted by the workflow itself;
- the integration suite then runs against that live API with
  `BASE_URL=http://127.0.0.1:8005`.

Two honesty rules learned the hard way (see RUNBOOK pitfalls #6 and #8):

- the DB host is `${{ vars.DB_HOST || 'localhost' }}`: GitHub maps service
  ports onto job localhost, **act** only resolves services by name
  (`--var DB_HOST=postgres`);
- the api is started with `setsid nohup … > /tmp/api.log 2>&1 &` because act
  kills each step's process group at teardown — a plain `&` server dies
  between steps;
- the integration step **refuses to pass on a skip**: it greps its own pytest
  output for `1 passed`, and dumps `/tmp/api.log` otherwise. A skip in CI is a
  vacuous green.

Observed results (real runs): `4 passed, 1 warning` and `1 passed in 0.28s`
inside CI; `1 passed in 0.76s` against the port-forwarded kind cluster.
