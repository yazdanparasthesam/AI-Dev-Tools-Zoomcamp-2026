# Release process (local, CI-enforced)

"Releasing" Agent Relay in this project means: a commit on `main` travels
through CI and, if every test passes, becomes the version running in the local
kind cluster. Nothing is deployed by hand; nothing red reaches the cluster.

## 1. Version identity

Every deploy builds one uniquely-tagged image:

```
TAG = relay-<GITHUB_RUN_NUMBER>-<short sha>      e.g. relay-1-77e9656
```

The tag is computed once (`steps.tag.outputs.TAG`) and reused by build,
`kind load`, `kubectl set image` and the post-deploy smoke, so at any moment
`kubectl get deployment app -o jsonpath='{.spec.template.spec.containers[0].image}'`
names the exact commit that is live. User-visible versioning rides along in
the dashboard heading (`Agent Relay` → `Agent Relay v2`, commit 77e9656).

## 2. The gate (Q6 in production terms)

```
commit on main
      │
      ▼
 job test ── starter suite (sqlite) ── integration suite (live api + postgres service)
      │ green                                    │ red
      ▼                                          ▼
 job deploy                              job deploy SKIPPED
  build → kind load → set image →        cluster keeps serving the
  rollout status (WAIT) → smoke          previous tag; humans investigate
```

Evidence collected on real runs: a poisoned assertion / a crashing boot / a
failing service pull each left the live version untouched (`agent-relay:local`
through runs 1-4, `relay-1-77e9656` afterwards); the green run rolled out
replica-by-replica with `rollout status` blocking until
`deployment "app" successfully rolled out`.

## 3. Release checklist

1. working tree clean, `git status --short` empty;
2. both suites green locally (`uv run pytest test_agent_relay.py -q`,
   `uv run pytest tests/integration -q` with a live target);
3. commit; run the workflow (GitHub push, or `act` locally with
   `--var DEPLOY_TARGET=kind-local`);
4. watch for: `1 passed` in CI, `Successfully tagged`, `kind load` …
   `loading...`, `image updated`, `successfully rolled out`, smoke tag;
5. restart the port-forward (it dies with the old pods), then verify content,
   e.g. `curl -s localhost:8000 | grep -o '<h1>[^<]*</h1>'`;
6. record evidence (log tail / screenshot) in the runbook.

## 4. Deliberate-break checklist (drill, homework 6c)

1. poison one assertion in `tests/integration/test_task_flow.py`
   (**do not commit**);
2. run the workflow → integration step fails → `Job failed` → deploy skipped;
3. prove the live version is unchanged (image jsonpath + heading curl);
4. `git checkout -- tests/integration/test_task_flow.py`; tree clean again.

## 5. Rollback

Images stay in the node's containerd store (nothing is ever deleted), so
rollback is one command plus a wait:

```bash
kubectl set image deployment/app app=agent-relay:<previous-tag>
kubectl rollout status deployment/app --timeout=180s
```

`kubectl rollout undo deployment/app` works too, since the Deployment keeps
revision history.

## 6. Known issues pointer

Operational surprises (corporate proxy/DNS, nftables lockdown, psycopg scheme,
SQLite `BEGIN IMMEDIATE` vs `FOR UPDATE SKIP LOCKED`, act's service networking,
process-group teardown, docker.sock double mount, TLS-timeout kubeconfig
repoint, stale registry credentials, dying port-forwards) are each written up
with diagrams in `HW3-RUNBOOK.md`, pitfalls #1-#11.
