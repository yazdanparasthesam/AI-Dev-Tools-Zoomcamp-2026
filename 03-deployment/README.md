# HW3 submission kit - Agent Relay (module 03: Containerize and Deploy)

Everything produced for DataTalksClub AI Dev Tools Zoomcamp 2026 homework 3,
packed from a real, screenshot-evidenced run on a corporate-network Ubuntu box.
`RUNBOOK.md` is the full narrative (steps 1-6, pitfalls #1-#11 with diagrams);
this README is the map.

## Layout

```
hw3-submission-kit/
├── README.md                  this file
├── RUNBOOK.md                 full illustrated runbook (evidence/ paths)
├── homework-3-answers.md      the six answers, all boxes ticked
├── faq-issue-draft.md         paste-ready FAQ proposal (file it yourself!)
├── repo-files/                drop-in tree mirroring the repo root
│   ├── .github/workflows/ci.yml   test job + gated deploy job (act-ready)
│   ├── Dockerfile                 python:3.11-slim + uv, EXPOSE 8000, 0.0.0.0
│   ├── compose.yaml               service named `postgres` (Q4)
│   ├── dashboard.html             heading already at "Agent Relay v2" (6b)
│   ├── database.py / storage.py   PostgreSQL-port seam (_is_sqlite, SKIP LOCKED)
│   ├── tests/integration/test_task_flow.py   SPEC scenario 1 as an API test (Q2)
│   ├── k8s/secret.yaml|postgres.yaml|app.yaml  PVC+probes+replicas (Q5)
│   └── docs/testing.md|deployment.md|release-process.md   module deliverables
├── scripts-and-patches/
│   ├── postgres-port.patch    the SQLite->PostgreSQL claim-locking seam
│   ├── act-run.sh             the exact act invocation used for green runs
│   ├── prune-docker-creds.py  pitfall #10 cleanup (stale registry creds)
│   ├── port-forward-loop.sh   pitfall #11 self-healing port-forward
│   └── verify-deploy.sh       live heading + live image tag in one shot
└── evidence/                  26 curated screenshots (green runs only,
                               no duplicates; failed-run frames deliberately excluded)
```

## Putting it into the repo

```bash
cp -r repo-files/. <your-fork>/          # mirrors paths, incl. .github/
cd <your-fork> && git add -A && git commit -m "hw3: ci, k8s, docs, tests" && git push origin main
```

Files already present in a repo that followed the runbook are identical to
these copies; `docs/` and this kit's additions are the new parts.

## Evidence index

| file | what it proves |
|---|---|
| `evidence/01-step1-uv-sync-pytest.png` | Step 1: uv sync + starter suite green on the fresh fork (Q1 baseline). |
| `evidence/03-step1-dashboard-empty.png` | Step 1: dashboard served by the dev server, empty task list. |
| `evidence/05-step1-grep-clean.png` | Step 1: reading the code - agents claim tasks from the DB via HTTP API (Q1). |
| `evidence/06-step2-curl-flow.png` | Step 2: SPEC scenario 1 driven live with curl: queued -> processing -> completed. |
| `evidence/08-step2-dashboard-completed.png` | Step 2: dashboard shows the completed task with its output. |
| `evidence/10-step2-integration-gate.png` | Step 2: the new API integration test passes against the live dev server (Q2). |
| `evidence/12-step3-dockerfile.png` | Step 3: the Dockerfile (python:3.11-slim + uv, EXPOSE 8000, --host 0.0.0.0). |
| `evidence/13-step3-build-finished.png` | Step 3: docker build -t agent-relay:local succeeds. |
| `evidence/15-step3-dashboard-container.png` | Step 3: dashboard served from the container through the published port (-p, Q3). |
| `evidence/16-step3-gate-green.png` | Step 3: integration test green against the containerized relay. |
| `evidence/17-step4-patch-in-fork.png` | Step 4: postgres-port.patch applied (SQLite BEGIN IMMEDIATE vs PG SKIP LOCKED). |
| `evidence/18-step4-compose-file.png` | Step 4: compose.yaml with service named postgres (Q4 hostname). |
| `evidence/19-step4-apply-and-up.png` | Step 4: patch apply + compose up, API boots against PostgreSQL. |
| `evidence/20-step4-gate-green.png` | Step 4: integration green vs compose stack + rows verified inside PG. |
| `evidence/22-step5-compose-down-kind-create.png` | Step 5: kind cluster "relay" created. |
| `evidence/23-step5-load-and-manifests.png` | Step 5: kind load docker-image + k8s/ manifests (Deployment keeps replicas, Q5). |
| `evidence/24-step5-apply-rollout-pods.png` | Step 5: kubectl apply, rollout, pods Running (app x2 + postgres). |
| `evidence/25-step5-dashboard-portforward.png` | Step 5: dashboard reached through kubectl port-forward svc/app. |
| `evidence/27-step5-two-replicas.png` | Step 5: both replicas serving - Deployment manages replicas/updates (Q5). |
| `evidence/50-step5-integration-via-forward-green.png` | Step 5 closing line: integration suite 1 passed via the port-forward. |
| `evidence/51-step6-6b-before-sed-commit.png` | Step 6b: before-shot heading, the sed, grep check, commit 77e9656. |
| `evidence/57-step6-run5-test-green.png` | Step 6: CI test job green inside act - 4 passed + 1 passed vs postgres service. |
| `evidence/62-step6-run5-load-rollout.png` | Step 6: kind load + rollout status WAIT, replica by replica. |
| `evidence/63-step6-run5-smoke.png` | Step 6: smoke prints deployment image relay-1-77e9656; Job succeeded x2. |
| `evidence/64-step6-forward-restart.png` | Step 6: port-forward restarted after the rollout (pitfall #11). |
| `evidence/66-step6-6b-v2-curl.png` | Step 6b verified: live cluster serves <h1>Agent Relay v2</h1>.
