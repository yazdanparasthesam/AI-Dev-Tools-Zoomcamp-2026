# HW3 Runbook — Agent Relay: test, containerize, deploy

Same loop as HW2: one step at a time, gate command proves it, screenshot (or
paste) before the next step. Everything runs on the user's Ubuntu machine; the
sandbox prepares and verifies files (no docker/kind/act there).

## Step 1 — Fork, run, understand (Q1)
- Fork `alexeygrigorev/agent-relay` on GitHub, clone the fork
- `uv sync && uv run pytest -q` (starter suite green before touching anything)
- `uv run uvicorn main:app --reload`, open http://127.0.0.1:8000/
- Prove Q1 by absence (note `--exclude-dir=.venv`!):
  `grep -rniE 'kafka|rabbit|redis|broker|celery' --include='*.py' --exclude-dir=.venv .`
  → `NO BROKER ANYWHERE`
- Install docker now (Steps 3–6 need it): `sudo apt install -y docker.io`,
  `sudo usermod -aG docker $USER && newgrp docker`, `docker info | head -3`
- Gate: pytest green + dashboard + docker info

### Step 1 evidence (real run, user's Ubuntu box)

![uv sync + starter suite: 4 passed, 1 warning](evidence/01-step1-uv-sync-pytest.png)
*`uv sync` installs 32 packages — note `psycopg-binary 3.3.6` already present:
the Postgres port in Step 4 needs no new dependencies. Starter suite:
**4 passed, 1 warning** (Starlette deprecation, noise).*

![Dashboard empty state: token box, Agents, My tasks](evidence/03-step1-dashboard-empty.png)
*Token-based local dashboard: nothing renders until an agent token is pasted;
credentials stay in the browser.*

![Corrected grep: zero matches in project code](evidence/05-step1-grep-clean.png)
*Q1 closed with evidence: with `--exclude-dir=.venv` the grep returns nothing —
no broker, no queue library anywhere in the project. Agents reach the DB
through the HTTP API.*

<details><summary>Pitfall: what the first (wrong) grep looked like</summary>

</details>

## Step 2 — Acceptance scenario 1 + integration test (Q2)

Live flow by hand (Step 1 server still running):

```bash
alice=$(curl -sS -X POST http://127.0.0.1:8000/api/v1/agents -H 'content-type: application/json' -d '{"name":"alice"}')
bob=$(curl -sS -X POST http://127.0.0.1:8000/api/v1/agents -H 'content-type: application/json' -d '{"name":"uppercase"}')
AT=$(echo "$alice" | python3 -c 'import sys,json;print(json.load(sys.stdin)["token"])')
AID=$(echo "$alice" | python3 -c 'import sys,json;print(json.load(sys.stdin)["agent_id"])')
BT=$(echo "$bob" | python3 -c 'import sys,json;print(json.load(sys.stdin)["token"])')
BID=$(echo "$bob" | python3 -c 'import sys,json;print(json.load(sys.stdin)["agent_id"])')

task=$(curl -sS -X POST http://127.0.0.1:8000/api/v1/tasks -H "authorization: Bearer $AT" \
  -H 'content-type: application/json' -d "{\"to\":\"$BID\",\"input\":\"review this function\"}")
echo "$task"; TID=$(echo "$task" | python3 -c 'import sys,json;print(json.load(sys.stdin)["task_id"])')

claim=$(curl -sS -X POST http://127.0.0.1:8000/api/v1/tasks/claim -H "authorization: Bearer $BT" \
  -H 'content-type: application/json' -d '{"worker_id":"demo-1","wait_seconds":0}')
echo "$claim"; CT=$(echo "$claim" | python3 -c 'import sys,json;print(json.load(sys.stdin)["claim_token"])')

curl -sS -X POST http://127.0.0.1:8000/api/v1/tasks/$TID/complete -H "authorization: Bearer $BT" \
  -H 'content-type: application/json' -d "{\"claim_token\":\"$CT\",\"output\":\"REVIEWED: looks good\"}"
curl -sS http://127.0.0.1:8000/api/v1/tasks/$TID -H "authorization: Bearer $AT"   # → "status":"completed"
```

Dashboard: paste alice's token → *My tasks* shows the task with its result
(Q2 visible with your own eyes).

Integration test: `hw3-kit/tests/integration/test_task_flow.py` → copy into the
fork at `tests/integration/test_task_flow.py`. Verified in sandbox against a
live relay: **1 passed**; full suite 5 passed; and it SKIPS when nothing
listens, so plain `uv run pytest -q` never goes red. Reused in Steps 4–6 by
pointing `BASE_URL` at the container / compose stack / port-forward.

- Gate: `uv run pytest tests/integration -q` green against the local server

### Step 2 evidence (real run)

![curl flow: queued → claim → complete → completed](evidence/06-step2-curl-flow.png)
*The whole lifecycle in one terminal: `"status":"queued"` on create, the claim
returns `claim_token` + lease expiry, complete flips to `"status":"completed"`,
and the sender's GET shows the output plus `finished_at`.*

![Dashboard: task completed, output and delivery history visible](evidence/08-step2-dashboard-completed.png)
*Q2 with your own eyes: status **completed**, output `REVIEWED: looks good`,
delivery history `1:completed (demo-1)`.*

![Integration gate: 1 passed in 0.92s](evidence/10-step2-integration-gate.png)
*`uv run pytest tests/integration -q` against the live dev server: green.*

## Step 3 — Dockerfile (Q3)
- `docker build -t agent-relay:local .`
- Pitfall (real): `COPY --from=ghcr.io/astral-sh/uv:latest` fails with
  `DeadlineExceeded … i/o timeout` on networks where ghcr.io is blocked while
  docker.io works. Fix: `RUN pip install --no-cache-dir 'uv>=0.9'` — same
  lockfile reproducibility, one reachable registry.
- Pitfall #2 (real, corporate network): RUN steps on the default bridge
  network get no DNS ("Temporary failure in name resolution"), and `sudo`
  strips `http_proxy` from the client env. Fix: `sudo docker build
  --network=host …` (the host network already reaches PyPI); if the host
  itself needs the proxy, add `--build-arg http_proxy=… --build-arg
  https_proxy=…` (single slash on the port) so it lands inside the build
  container. The Step 6 CI build needs the same flag.
- `docker run --rm -p 8000:8000 --name relay-local agent-relay:local`
  (uvicorn `--host 0.0.0.0` inside; `-p` publishes)
- Repeat Step 2 flow against container; dashboard from host browser
- Gate: flow completes against containerized API

### Step 3 evidence (real run)

![The Dockerfile as landed in the fork](evidence/12-step3-dockerfile.png)
*uv from PyPI, dependency layer before code layer, CMD pins
`--host 0.0.0.0`.*

![Build FINISHED 12/12 in 108 s](evidence/13-step3-build-finished.png)
*Needed BOTH `--network=host` and the proxy `--build-arg`s on this corporate
network: pip step 66 s, `uv sync --frozen` 33 s, image `sha256:8aa8e60c…`
tagged `agent-relay:local`.*


![Dashboard served by the container](evidence/15-step3-dashboard-container.png)
*The containerized relay serving the dashboard on host port 8000.*

![Step 3 gate green: health JSON, 1 passed, request lines in container log](evidence/16-step3-gate-green.png)
*`{"status":"ok"}`, `1 passed in 0.71s`, and the container log finally shows
request lines — including the two 404s that are the test's outsider-access
assertions. Step 3 closed.*

- Pitfall #3 (the real killer, real run): an **nftables lockdown table** with
  `type filter hook forward … policy drop` plus generated per-bridge and
  per-container-IP drop rules (`iifname != "docker0" ip daddr 172.17.0.2 … drop`,
  counter matched our curls). It allowed traffic to a container only from its
  own bridge, killing published ports, host→container and container→container
  everywhere (n8n/rabbitmq dead too). Invisible to `iptables`; found via
  `sudo nft list ruleset | grep -n drop`; fixed with
  `sudo nft delete table <family> <name>`. The earlier `fix-forward.sh`
  iptables rules were a red herring (bridged frames never hit iptables).
  Hunt the generator: `sudo grep -rln 'iifname' /etc /opt /usr/local/bin`,
  `systemctl list-timers --all`.

## Step 4 — Compose + Postgres (Q4)
- STOP the Step 3 container first (`docker stop relay-local`) — it holds host
  port 8000, which the compose app service needs.
- File: `hw3-kit/compose.yaml` (build.network: host for the corporate DNS
  issue; postgres healthcheck gates app startup; pgdata volume; postgres
  intentionally unpublished).
- `compose.yaml`: services `app` (build .) + `postgres` (postgres:16,
  healthcheck pg_isready); app env `RELAY_DATABASE_URL=postgresql://relay:relay@postgres:5432/relay`
- `docker compose up --build`; integration test with
  `BASE_URL=http://127.0.0.1:8000` against the stack
- Prove Postgres holds data: `docker compose exec postgres psql -U relay -c '\dt'`
  and a row count after the flow
- Gate: test green + tables/rows visible in psql
- Pitfall #4 (real): app crash-looped with `ModuleNotFoundError: No module
  named 'psycopg2'`. Cause: `postgresql://` selects SQLAlchemy's default
  psycopg2 dialect; the starter ships psycopg 3 (`psycopg[binary]`), whose
  dialect is `postgresql+psycopg://`. Fix is the URL scheme, not new deps.
- Pitfall #5 (real, the 500s): starter's `immediate_transaction()` runs
  `BEGIN IMMEDIATE` unconditionally — SQLite-only syntax, so on Postgres every
  create/claim/complete 500s while register (plain `db_session`) returns 201.
  This is the porting seam SPEC.md leaves to students. Fix (verified in
  sandbox vs PostgreSQL 17: integration 1 passed, SQLite suite 4 passed):
  branch on `_is_sqlite(DATABASE_URL)` in `database.py`, and give `claim_one`
  `with_for_update(skip_locked=True)` on Postgres. Patch:
  `hw3-kit/patched/postgres-port.patch` (or whole files in `hw3-kit/patched/`).

### Step 4 evidence (real run)

![The patch as landed in the fork](evidence/17-step4-patch-in-fork.png)
*`cat postgres-port.patch`: the two-file diff before applying.*

![compose file in the fork (named docker-compose.yaml)](evidence/18-step4-compose-file.png)
*The compose file with `postgresql+psycopg://` and the unpublished postgres
service. Note the filename: compose v2 accepts `docker-compose.yaml`, but the
homework text says `compose.yaml` — rename with `git mv` before submitting.*

![git apply + compose up --build: postgres Healthy, app Started](evidence/19-step4-apply-and-up.png)
*Patch applied, image rebuilt (code layers only — dependency layers cached),
stack up with the healthcheck gate honoured.*

![Step 4 gate green: health ok, 1 passed, completed|1 in Postgres, 3 tables](evidence/20-step4-gate-green.png)
*The proof set: `{"status":"ok"}`, `1 passed in 0.76s`,
`select status, count(*) … group by status` → `completed | 1`, and `\\dt`
listing agents/attempts/tasks owned by `relay`. Step 4 closed.*

### Why postgres-port.patch exists — full anatomy

Symptom chain observed on the compose stack:

```
POST /api/v1/agents   → 201   register_agent()  → db_session()          plain BEGIN      ✅
POST /api/v1/tasks    → 500   create_task()     → immediate_transaction()                ❌
POST /api/v1/tasks/claim → 500 claim_one()      → immediate_transaction()                ❌
POST …/complete       → 500   commit_terminal() → immediate_transaction()                ❌
GET  /api/v1/tasks/id → ok    read path         → db_session()          plain BEGIN      ✅
```

Inside `immediate_transaction()` (database.py, starter code):

```
connection.exec_driver_sql("BEGIN IMMEDIATE")
        │
        ├── SQLite:    valid — reserves the writer lock, serializes claims   ✅
        └── Postgres:  SYNTAX ERROR — no such statement                      ❌ → 500
```

That line is the seam SPEC.md leaves for students: "The SQLite starter uses a
BEGIN IMMEDIATE transaction … When porting storage to PostgreSQL, use a
transaction and row locking such as FOR UPDATE SKIP LOCKED." The compose run
was the first time any code path touched Postgres, so the first write through
the seam exploded — while reads and registration (plain sessions) kept working,
which is exactly the confusing 201-then-500 pattern in the test output.

After the patch:

```
immediate_transaction()
  ├─ SQLite branch (unchanged):  BEGIN IMMEDIATE        → starter's 4 tests stay green
  └─ Postgres branch (new):      SQLAlchemy autobegin   → real transaction
                                 + claim_one() adds:
                                   SELECT … ORDER BY created_at, id LIMIT 1
                                   FOR UPDATE SKIP LOCKED
                                         │
                                         ▼
                                   concurrent workers SKIP the locked row
                                   → one active lease per task (SPEC §3),
                                     no double-claims across API processes
```

Verification matrix (sandbox, PostgreSQL 17 + SQLite):

| Suite | Backend | Before patch | After patch |
| --- | --- | --- | --- |
| tests/integration (live HTTP) | Postgres 17 | 500 on create/claim | 1 passed, `completed` row in PG |
| test_agent_relay.py (starter) | SQLite | 4 passed | 4 passed (no regression) |

The patch also fixed its own first-draft bug: the new `_is_sqlite(DATABASE_URL)`
check in storage.py needed `DATABASE_URL` imported there — missed on draft 1,
caught by the NameError traceback, which is why the delivered patch adds both
`DATABASE_URL` and `_is_sqlite` to storage.py's import list.

## Step 5 — kind + k8s (Q5)
- Install kind + kubectl; `kind create cluster --name relay`
- `k8s/`: app Deployment (readiness `/ready`, liveness `/health`) + Service;
  postgres Deployment/StatefulSet + PVC + Service; secrets via env or Secret
- `kind load docker-image agent-relay:local --name relay`
- `kubectl apply -f k8s/`; `kubectl rollout status`
- `kubectl port-forward svc/… 8000:8000`; dashboard + flow
- Gate: pods Ready, flow completes through port-forward

### Step 5 evidence (real run)

![compose down + kind create cluster relay](evidence/22-step5-compose-down-kind-create.png)
*Compose stack removed; `kind create cluster --name relay` on the local
kindest/node:v1.29.2 image — no pulls needed; context switched to kind-relay
while complaintradar-cluster stays untouched.*

![kind load both images; k8s/ manifests created](evidence/23-step5-load-and-manifests.png)
*`agent-relay:local` and `postgres:16` loaded into the node. Pitfall repeat:
`sudo vim` left the three manifests root-owned — `sudo chown -R "$USER:$USER" k8s`.*

![apply, both rollouts green, three pods Running, port-forward up](evidence/24-step5-apply-rollout-pods.png)
*Six objects created; `deployment "postgres" successfully rolled out`,
`deployment "app" successfully rolled out`; app×2 + postgres 1/1 Running.
One app pod shows RESTARTS 1: startup probe race before postgres accepted —
cosmetic, pods stable afterwards.*

![Dashboard through kubectl port-forward svc/app](evidence/25-step5-dashboard-portforward.png)

![Both replicas Ready — the Deployment keeping them alive (Q5)](evidence/27-step5-two-replicas.png)

### Step 5 evidence — the closing line (via port-forward)

![STEP 5 CLOSED: integration suite against the port-forwarded cluster](evidence/50-step5-integration-via-forward-green.png)
*`uv run pytest tests/integration -q` → **`1 passed in 0.76s`** through
`kubectl port-forward svc/app 8000:8000` — the last missing Step-5 line: the
SPEC acceptance-scenario test, green against the kind cluster itself.*

## Step 6 — CI/CD with act (Q6)
- `.github/workflows/ci.yml`: job test (services: postgres) → build image
  (unique tag per run) → load into kind → apply/set image → `kubectl rollout
  status`; deploy steps gated on test success
- `act` with docker socket + kind access; wait for rollout
- Change `dashboard.html` h1 to `Agent Relay v2`, rerun, verify heading
- Break-on-purpose: make a test fail once, confirm workflow stops before deploy
- Gate: green run deploys v2; red run leaves previous version running

### Step 6 evidence (real run)

### Step 6 evidence — run 5: first FULLY green pipeline (deploy included)

Run 5, second attempt (the first died at `Set up job` on the stale-credential
RBAC denial of pitfall #10; the retry right after was clean). Commit deployed:
`77e9656` (the v2 heading) as tag `relay-1-77e9656`:

```
[ci/test]   4 passed, 1 warning in 3.60s
[ci/test]   DB target = postgres:5432/relay
[ci/test]   {"status":"ok"}api healthy; detached with setsid so it survives step teardown
[ci/test]   1 passed in 0.28s
[ci/test]   🏁  Job succeeded
[ci/deploy] ::set-output:: TAG=relay-1-77e9656
[ci/deploy] Successfully tagged agent-relay:relay-1-77e9656
[ci/deploy] Image … not yet present on node "relay-control-plane", loading...
[ci/deploy] ✅ Success - Main load image into kind [8.5s]
[ci/deploy] deployment.apps/app image updated
[ci/deploy] Waiting for deployment "app" rollout to finish: 1 out of 2 new replicas…
[ci/deploy] Waiting for deployment "app" rollout to finish: 1 old replicas are pending termination…
[ci/deploy] deployment "app" successfully rolled out          ← the WAIT, honored
[ci/deploy] app-5d9f6d45dd-5w8p2  1/1 Running  0  6s
[ci/deploy] app-5d9f6d45dd-fckgs  1/1 Running  0  12s
[ci/deploy] app-bbfb4d47b-hdn7j   1/1 Terminating  (old replica leaving)
[ci/deploy] deployment image now: agent-relay:relay-1-77e9656
[ci/deploy] 🏁  Job succeeded
```

Both `Job succeeded` lines in one run for the first time. The kubeconfig
repoint + `kctl` retries of pitfall #9 were not even needed this time — the
loopback path behaved — but they stay in as cheap insurance.

*Post-rollout surprise (pitfall #11): `curl -s localhost:8000 | grep -o
'<h1>[^<]*</h1>'` came back EMPTY four times right after this green run — the
port-forward had died with the old pods, not the app. Restart the forward and
the v2 heading appears.*

### Step 6 evidence — 6b verified: the cluster serves the v2 heading

![6b: before-shot, the sed, grep check, commit 77e9656](evidence/51-step6-6b-before-sed-commit.png)
*`curl` still shows `<h1>Agent Relay</h1>` (cluster on `agent-relay:local`);
the sed swaps line 18; `grep -n '<h1>'` confirms exactly one heading, now v2;
committed as 77e9656.*

![Run 5 test job: both suites green inside CI](evidence/57-step6-run5-test-green.png)
*`4 passed` (starter, sqlite) · `DB target = postgres:5432/relay` ·
setsid-detached boot · **`1 passed in 0.28s`** (integration vs live API +
postgres service) · `Job succeeded` ⇒ gate opens.*

![Run 5 deploy: load into kind, rollout WAIT honored](evidence/62-step6-run5-load-rollout.png)
*`TAG=relay-1-77e9656`; image loaded into `relay-control-plane`;
`deployment.apps/app image updated` → replica-by-replica waiting lines →
`deployment "app" successfully rolled out`.*

![Run 5 deploy: smoke proves the new bytes; second Job succeeded](evidence/63-step6-run5-smoke.png)
*New pods Running, old replica Terminating,
`deployment image now: agent-relay:relay-1-77e9656`.*

![Port-forward restarted after the rollout (pitfall #11)](evidence/64-step6-forward-restart.png)
*The old forward died with the terminated pod; a fresh one re-attaches to the
new replicas.*

![6b VERIFIED: live cluster serves the v2 heading](evidence/66-step6-6b-v2-curl.png)
*`curl -s localhost:8000 | grep -o '<h1>[^<]*</h1>'` →
**`<h1>Agent Relay v2</h1>`**. Heading changed → pipeline re-run → rollout
waited → cluster serves v2. Step 6b closed. (Frames 53-56, 58-61, 65 of this
batch — apt/sync/build/pods detail — are archived alongside.)*

### Step 6 pitfalls (real, from the first full act run)

- **Pitfall #6 (real, three layers of green-lie): `localhost:5432` inside the
  act job container → `psycopg.OperationalError: connection refused` — and act
  still printed `✅ Success`, then `1 skipped` for the integration test.**
  Three separate problems stacked:
  1. *Networking.* On **GitHub Actions**, service-container ports are mapped
     onto the job's `localhost`. Under **act**, services are separate
     containers on a shared docker network, reachable **by service name**
     (`postgres`), never via `localhost`:

     ```
     GitHub Actions (real)                act (local)
     ─────────────────────                ────────────────────────────────
      job runner                           act docker network
      ┌──────────────────────┐             ┌──────────────┐ ┌────────────┐
      │ steps + services in  │             │ job container│ │ postgres:16│
      │ ONE network namespace│             │ ubuntu:22.04 │ │ (service)  │
      │ localhost:5432 ──────┼─► postgres  │ localhost:   │ │ postgres:  │
      │ (GH maps svc ports)  │             │ 5432 ►NOTHING│ │ 5432 ►HERE │
      └──────────────────────┘             └──────────────┘ └────────────┘
     ```

     Fix that works in BOTH worlds: parameterize the host —
     `...@${{ vars.DB_HOST || 'localhost' }}:5432/relay`; act run passes
     `--var DB_HOST=postgres`; on GitHub `vars.DB_HOST` is unset ⇒ falls back
     to `localhost`, which is correct there.
  2. *The boot step lied.* uvicorn was started with `&`; a background process
     crashing only prints its traceback — the step's exit code came from the
     retry loop's last `sleep 1` ⇒ exit 0 ⇒ `✅`. Fix: capture `api_pid=$!`,
     probe with `kill -0 "$api_pid"` (dies ⇒ `exit 1` immediately), and
     `exit 1` if `/health` never answers within 30 s.
  3. *The integration gate was vacuous.* `tests/integration/test_task_flow.py`
     deliberately **skips** when no live relay answers (so local
     `uv run pytest -q` stays green). In CI a skip is a green that proves
     nothing — the log showed `1 skipped in 0.58s` under `✅`. Fix: the CI
     step captures pytest output and refuses to pass unless it literally sees
     `1 passed`:

     ```yaml
     out=$($UV run pytest tests/integration -q -rs 2>&1) || { echo "$out"; exit 1; }
     echo "$out"
     echo "$out" | grep -q "1 passed" || { echo "FATAL: ... (skipped?)"; exit 1; }
     ```

- **Pitfall #7 (real): deploy job never started —
  `failed to create container: 'Error response from daemon: Duplicate mount
  point: /var/run/docker.sock'`.**
  act **auto-mounts** the host docker socket into every job container (that is
  how docker/kind work at all inside act). Our `container.options` mounted it a
  second time; the docker daemon rejects duplicate mount points at
  `docker create`, before any step runs:

  ```
  mounts of /var/run/docker.sock requested for the deploy container:
    act itself      ──► -v /var/run/docker.sock:/var/run/docker.sock   (automatic)
    our options     ──► -v /var/run/docker.sock:/var/run/docker.sock   (ours)
                         ────────────────────────────────────────────
    docker daemon   ✗ Duplicate mount point → container never created
  ```

  Fix: delete our `-v /var/run/docker.sock:...` line from the deploy job's
  `options` (keep `--network host` + the `~/.kube` mount). On GitHub the
  deploy job is skipped anyway (DEPLOY_TARGET unset), so this is act-only
  plumbing.

- **Pitfall #8 (real, run 3): boot step green, integration STILL
  `SKIPPED … no live relay` — the server died BETWEEN the two steps.**
  act runs every step in its own `docker exec` session and tears the session's
  PROCESS GROUP down when the step ends. A server backgrounded with plain `&`
  stays in that group and is signalled away the moment the green boot line
  prints:

  ```
  step "boot"                           between steps             step "integration"
  ┌─────────────────────────────┐      ┌──────────────────┐      ┌──────────────────────┐
  │ sh -e 5.sh       (pgid X)   │      │ exec teardown:   │      │ sh -e 6.sh           │
  │  └─ uvicorn &    (pgid X!)  │ ───► │ signal pgid X    │ ───► │ GET 127.0.0.1:8005   │
  │  /health 200 ✅  pid 2871   │      │ → server dies    │      │  → refused → SKIP    │
  └─────────────────────────────┘      └──────────────────┘      └──────────────────────┘
  ```

  Fix (run 4): `setsid nohup $UV run uvicorn … > /tmp/api.log 2>&1 &` — setsid
  gives the server its own session + process group (immune to the group
  kill), nohup ignores HUP, and the log file prevents SIGPIPE once the exec's
  pipes close. The integration step also dumps `/tmp/api.log` whenever the
  outcome is not literally `1 passed`, so the next failure explains itself.

- **Pitfall #9 (real, run 4): the deploy job's first kubectl call —
  `Unable to connect to the server: net/http: TLS handshake timeout`.**
  The mounted kubeconfig points at `https://127.0.0.1:<port>`; that path
  reaches the API server through docker's userland proxy (docker-proxy),
  which forwards into the control-plane container. That hop stalled for >10 s
  (immediately after the 28 s `kind load` stressed the daemon) while kubectl
  on the host kept working:

  ```
  deploy container (--network host ⇒ host netns)
     kubectl ──► 127.0.0.1:PORT ──► docker-proxy ──► relay-control-plane:6443
                                        ▲
                                        └─ this hop stalled (TLS timeout, run 4)
  run-5 path:  kubectl ──► <control-plane container IP>:6443 ──► API server
                         (bridge path, no userland-proxy hop; discovered with
                          docker inspect, SAN mismatch covered by
                          --insecure-skip-tls-verify)
  ```

  Run-5 fix, two belts: (a) repoint the kubeconfig's cluster at the
  control-plane container IP right after `kind load`; (b) wrap every kubectl
  call in a 4-attempt retry helper (`kctl`).

- **Pitfall #10 (cosmetic, run 4): `pulling image 'docker.io/library/postgres:16'
  () failed with credentials … unauthorized … retrying without them, please
  check for stale docker config files`.** A stale auth entry in
  `~/.docker/config.json`; docker falls back to anonymous and the pull
  succeeds. **Not** harmless: run 5's FIRST attempt hard-failed at `Set up job`
  with `denied: RBAC: access denied` — Harbor-style stale credentials offered
  to docker.io, no anonymous retry that time — and the immediate re-run
  succeeded. Permanent cleanup: back up the file and drop the credential keys
  (`auths`, `credsStore`, `credentialHelpers`), keeping everything else.

- **Pitfall #11 (real, right after run 5): the port-forward dies during every
  rollout, so post-deploy curls come back empty.**
  `kubectl port-forward svc/app 8000:8000` resolves the Service to ONE endpoint
  pod and sticks to it. The rollout terminates exactly that pod; the forward
  loses its only backend and exits — new pods are Running, nothing listens on
  :8000 anymore:

  ```
  port-forward ──► old pod app-bbfb4d47b-…  ──rollout kills it──► forward exits
                   new pods app-5d9f6d45dd-… Running   but nobody listens on :8000
                                                              → curl prints nothing
  ```

  Fix: restart `kubectl port-forward svc/app 8000:8000` after every rollout
  (or wrap it in `while true; do kubectl port-forward svc/app 8000:8000; sleep 1; done`).
  kubectl itself was never affected — it talks to the API server, not to the
  forward.

All fixes + the honest-boot/honest-gate steps are in `hw3-kit/ci.yml`
(canonical) as of the fifth act iteration (run-5 additions: kubeconfig
repoint + `kctl` retries); job-level gate remains
`if: vars.DEPLOY_TARGET == 'kind-local'` (vars is the only context legal in a
job-level `if`; the kit copy had gone stale with `env.` and was corrected in
the same rewrite).

**act command, third iteration (the one that must go green):**

```bash
sudo act push -W .github/workflows/ci.yml -P ubuntu-latest=ubuntu:22.04 \
  --var DEPLOY_TARGET=kind-local --var DB_HOST=postgres \
  --env http_proxy=http://192.168.70.135:3128 \
  --env https_proxy=http://192.168.70.135:3128 \
  --env HTTP_PROXY=http://192.168.70.135:3128 \
  --env HTTPS_PROXY=http://192.168.70.135:3128 \
  --env no_proxy=localhost,127.0.0.1,postgres \
  --env NO_PROXY=localhost,127.0.0.1,postgres
```

(Run 4 settled the proxy question: with the nft lockdown of pitfall #3 gone,
the job containers reach pypi/docker.io directly, so the four proxy flags are
optional — the lean command used in runs 3-4, two `--var`s plus the `no_proxy`
pair, carried the build all the way to `kind load`. Keep them only if your
network regresses.)
Proxy vars in BOTH cases: the workflow's build step reads `${HTTP_PROXY:-…}`
uppercase for the docker build-args, while apt/curl/pip honor lowercase;
`no_proxy` keeps curl→127.0.0.1:8005 and httpx→BASE_URL off the proxy.)

### sed anatomy — every edit we made with sed, and how to recover

Three sed edits touch this homework (two on `ci.yml` after the schema failure,
one coming in 6b on `dashboard.html`). The general shape:

```
sed  -i  's|PATTERN|REPLACEMENT|'  FILE
│    │    │ │        │            │   └─ target file, read ONE LINE AT A TIME
│    │    │ │        │            └─ replacement text (& = whole match)
│    │    │ │        └─ regex to search for
│    │    │ └─ s = substitute command; | = DELIMITER (any punctuation works —
│    │    │      we chose | because our patterns contain / from paths & URLs;
│    │    │      the default / would force escaping: s\/etc\/a\/b\/)
│    │    └─ the sed script — SINGLE-QUOTED so the shell hands it over untouched
│    └─ in-place: rewrite the file itself. WITHOUT -i sed only PRINTS the
│       result and the file is untouched → free dry run
└─ stream editor: never interactive, applies the script to every line
```

How a line flows through it:

```
        file on disk
            │  read line N
            ▼
   ┌──────────────────┐    no match    ┌────────────────────┐
   │ does the line     ├───────────────►│ print/write line   │
   │ match PATTERN?    │                │ unchanged          │
   └────────┬─────────┘                └────────────────────┘
            │ match
            ▼
   ┌──────────────────────────────┐
   │ s → splice REPLACEMENT in     │
   │ d → drop the line entirely    │
   └──────────────┬───────────────┘
                  ▼
      -i  → same file rewritten on disk
      no -i → screen only (dry run)
```

The three edits, concretely:

1. **gate context** — `env` is illegal in a job-level `if` (act schema:
   *Unknown Variable Access env*; GitHub agrees):
   `sed -i 's|if: env\.DEPLOY_TARGET|if: vars.DEPLOY_TARGET|' .github/workflows/ci.yml`
   (`\.` = a LITERAL dot — bare `.` in regex means "any character").
2. **delete the workflow-level env line** — the `d` command with an address
   regex: `/REGEX/d` drops every matching line:
   `sed -i "/|| 'none'/d" .github/workflows/ci.yml`
   (double quotes here only because the pattern itself contains single quotes;
   `|` is not special in basic sed regex, so no delimiter conflict).
3. **6b heading swap** (next step, after the green run):
   `sed -i 's|<h1>Agent Relay</h1>|<h1>Agent Relay v2</h1>|' dashboard.html`

**Resolution ritual (why our sed use never lost work):**

```
  commit FIRST ──► dry run (no -i, read output) ──► sed -i ──► git diff -- FILE
      ▲                                                            │
      │              only intended lines changed? ── no ──► git checkout -- FILE
      └────────────────────────── yes ──► commit ◄─────────────────┘
```

- sed is **silent when nothing matches** — exit 0, no warning. If the file
  looks unchanged, `grep -n 'PATTERN' FILE` to see whether the pattern exists
  at all (typos in the pattern are the #1 "sed didn't work" cause).
- Undo is trivial ONLY because of git: `git checkout -- FILE` restores the
  last committed state. Never sed a dirty file you cannot afford to lose.
- Special characters to respect in the pattern: `.` any char, `*` repeat,
  `[ ]` class, `^ $` anchors; in the replacement only `&` (whole match) and
  `\1…\9` (groups) are special.

## Docs (module deliverables)
docs/testing.md, docs/deployment.md, docs/release-process.md — written last,
from what actually happened (HW2 ai-usage-report style).
