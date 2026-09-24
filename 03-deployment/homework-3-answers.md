# Homework 3 — answers & evidence

Deadline: Fri 2026-09-25 02:30 (user tz). Status: in progress.
Starter: https://github.com/alexeygrigorev/agent-relay (fork = submission repo).
All execution happens on the user's Ubuntu box (sandbox has no docker/kind/act).

| Q | Answer | Evidence |
| --- | --- | --- |
| 1 | **Agents claim tasks from a DB through an HTTP API** | SPEC.md: relay persists tasks in SQLite; workers poll `POST /api/v1/tasks/claim`; "No LLM is required", no broker anywhere (`grep -ri 'kafka\|rabbit\|redis\|broker' *.py` → nothing); dashboard is read-only over the API |
| 2 | **`completed`** | SPEC lifecycle: `queued -> processing -> completed / failed`. `POST /tasks/{id}/complete` "changes the task to `completed`"; sender reads it via `GET /tasks/{id}`. `delivered` is not a state anywhere in SPEC.md (attempt outcomes are processing/completed/failed/expired) |
| 3 | **`-p`** | `docker run -p 8000:8000 …` publishes the port; `--expose` only documents it inside container networks; `-v` mounts volumes; `--name` names the container |
| 4 | **`postgres`** | Compose service names are DNS names on the compose network; `localhost` inside the API container is the API container itself |
| 5 | **Deployment** | Declarative replica count + rolling updates; Service routes traffic, ConfigMap/Secret hold config |
| 6 | **Keep the existing version running and stop the deployment** | Gates exist so failed tests never reach the cluster; deleting or swapping tags under a failing build is how outages start |

## Verification status per step

- [x] Q1, Q2 — read from SPEC.md + starter code in sandbox clone (`/home/user/agent-relay-starter`)
- [x] Q2 — live: ran acceptance scenario 1 locally, saw `completed` in dashboard + integration test 1 passed (Step 2)
- [x] Q3 — built `agent-relay:local`, ran with `-p 8000:8000`, flow + integration test green against container (Step 3; required deleting an nft lockdown table first — see HW3-RUNBOOK pitfall #3)
- [x] Q4 — compose stack with `postgres` service, integration test against it (Step 4)
- [x] Q5 — kind cluster, k8s/ manifests, port-forward dashboard (Step 5)
- [x] Q6 — ci.yml via act, heading change to `Agent Relay v2` redeployed (Step 6)

## Repo additions planned (module deliverables + homework)

```
tests/integration/test_task_flow.py   # Q2 integration test, BASE_URL-driven
Dockerfile                            # python:3.11-slim, uvicorn --host 0.0.0.0
compose.yaml                          # app + postgres service
k8s/*.yaml                            # Deployment+Service, postgres+PVC, probes
.github/workflows/ci.yml              # test → build → load into kind → rollout
docs/testing.md, docs/deployment.md, docs/release-process.md
```

Starter facts that shape the artifacts:
- run: `uv sync && uv run uvicorn main:app --reload`; dashboard at `/`
- DB env: `RELAY_DATABASE_URL` (fallback `DATABASE_URL`), default `sqlite:///./agent-relay.db`
- `psycopg[binary]` already a dependency → Postgres port is config, not new deps
- tests honor `RELAY_DATABASE_URL` → CI can point them at the compose/k8s Postgres
- dashboard heading lives in `dashboard.html` line 18: `<h1>Agent Relay</h1>` (Step 6 target)
- worker: `uv run python main.py worker --base-url … --name … --credentials …`
- `/health` liveness, `/ready` checks real tables → perfect k8s probes
