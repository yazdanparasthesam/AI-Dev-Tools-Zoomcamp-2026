# Deploying Agent Relay

Four concentric targets, each one used and verified in this project:
bare process → container → Compose stack → local Kubernetes (kind), plus CI
that deploys to kind only when tests are green.

## 1. Bare process (development)

```bash
uv sync && uv run uvicorn main:app --reload        # http://127.0.0.1:8000
```

`/health` = liveness, `/ready` = real DB tables reachable.

## 2. Single container (Q3)

`Dockerfile`: `python:3.11-slim`, uv installed via pip, `uv sync --frozen
--no-dev` into `/opt/venv`, app copied in, `EXPOSE 8000`, and
`CMD ["uv","run","--no-sync","uvicorn","main:app","--host","0.0.0.0","--port","8000"]`
— the `--host 0.0.0.0` inside the image is what makes publishing a port
meaningful. Publish with **`-p`**:

```bash
docker build -t agent-relay:local .
docker run --rm -p 8000:8000 agent-relay:local
```

## 3. Compose with PostgreSQL (Q4)

`compose.yaml` defines a service literally named `postgres`; the API reaches
it at hostname **`postgres`** (Compose's built-in DNS), never `localhost`:
`RELAY_DATABASE_URL=postgresql+psycopg://relay:relay@postgres:5432/relay`.
Note the driver scheme: SQLAlchemy 2 + psycopg3 wants `postgresql+psycopg://`
(`psycopg2://` fails at import). Porting the storage layer required the
`postgres-port.patch` seam: SQLite keeps `BEGIN IMMEDIATE`, PostgreSQL uses
`SELECT … FOR UPDATE SKIP LOCKED` for claim leasing (SPEC.md sanctions row
locking). Verify data really lands in PG:
`docker compose exec postgres psql -U relay -d relay -c 'select status, count(*) from tasks group by 1'`.

## 4. kind + manifests (Q5)

```bash
kind create cluster --name relay
kubectl apply -f k8s/
```

`k8s/` contains: `Secret relay-db` (credentials), `PersistentVolumeClaim
pgdata` + `Deployment postgres` (postgres:16, `pg_isready` probes) + its
`Service`, and `Deployment app` (replicas: 2, `imagePullPolicy: Never`,
initContainer waiting for postgres, `/ready` + `/health` probes) + `Service
app`. The **Deployment** is the resource that keeps replicas running and
orchestrates updates (Q5). Images never leave the host: build with docker,
then `kind load docker-image <tag> --name relay` copies them into the node's
containerd store (there is no registry; `Never` forbids pulling).

Dashboard access: `kubectl port-forward svc/app 8000:8000`.
Gotcha (RUNBOOK #11): a port-forward pins ONE endpoint pod; every rollout
terminates that pod and kills the forward — restart it after deploys.

## 5. CI-driven deploy (Q6)

`.github/workflows/ci.yml`: job `test` (starter + integration vs a postgres
service) → job `deploy` (`needs: test`, gated by
`if: vars.DEPLOY_TARGET == 'kind-local'`) builds `agent-relay:relay-<run>-<sha>`
(unique per version), `kind load`s it, `kubectl set image`, and **waits**:
`kubectl rollout status deployment/app --timeout=180s`, then smokes
`kubectl get deployment app -o jsonpath='{.spec.template.spec.containers[0].image}'`.
Failed tests ⇒ deploy skipped ⇒ the running version stays up (Q6).
Locally the whole workflow executes with **act**:

```bash
sudo act push -W .github/workflows/ci.yml -P ubuntu-latest=ubuntu:22.04 \
  --var DEPLOY_TARGET=kind-local --var DB_HOST=postgres \
  --env no_proxy=localhost,127.0.0.1,postgres --env NO_PROXY=localhost,127.0.0.1,postgres
```

act-specific plumbing worth knowing: services resolve by name, not localhost
(#6); act auto-mounts `/var/run/docker.sock`, so the workflow must not mount
it again (#7); step process groups die at teardown, hence `setsid nohup`
(#8); the kubeconfig's `127.0.0.1:<port>` path goes through docker's userland
proxy and once stalled with a TLS handshake timeout, so the deploy job
repoints the cluster at the control-plane container IP and retries kubectl
(#9); stale `~/.docker/config.json` credentials can make service pulls fail
with `RBAC: access denied` — prune `auths`/`credsStore` (#10).
