# HW4 — Order Tracker: observability + autonomous incident response (complete repo)

This archive is the complete repository state: instrumented app, Dockerfile,
tests, observability stack, incident responder, security audit, docs, answers
and evidence. Extract anywhere; no other files required.

## First run

    unzip hw4-github-upload.zip -d order-tracker && cd order-tracker
    cp .env.example .env                    # optional: only for the PAT auth channel
    sudo docker build -t order-tracker:local .
    sudo docker build -t order-tracker-responder:local ./incident-response
    sudo docker compose up -d --wait
    curl -i http://localhost:8000/healthz   # -> 200 {"status":"ok"}

Grafana http://localhost:3000 (admin/admin) · responder http://localhost:8001/healthz ·
Prometheus targets via collector :8889.

## .env and the Copilot token

`.env` is git-ignored and deliberately NOT shipped — it would carry a live
secret. Create it from `.env.example`, then either paste a PAT with the
"Copilot Requests" permission into COPILOT_GITHUB_TOKEN, or rely on the mounted
OAuth store (RUNBOOK episode T5-6). The responder launch gate accepts either;
with neither it records observe-only instead of launching the agent.

## Layout

    app/ static/ tests/ Dockerfile pyproject.toml uv.lock
                                      instrumented FastAPI app: OTel metrics+logs+traces with
                                      route+status labels; month-end-safe express estimate
    compose.yaml                      app + collector + prometheus + loki + tempo + grafana + responder
    observability/                    collector, prometheus, loki, tempo, grafana provisioning,
                                      dashboard.json, alerts.yaml, contact points, notification policy
    incident-response/                responder (POST /alerts :8001), autonomy-policy.yaml,
                                      response.schema.json, collect-evidence.sh, runbooks/, incidents/
    security-audit/                   audit brief, findings schema, capability table, runs, credentials playbook
    docs/operations-and-security-report.md   incident-by-ID reconstruction + findings F-01..F-05
    RUNBOOK.md                        step-by-step run, pitfalls #1-#9, episodes T5-1..7 / T6-1..7
    ANSWERS.md / FAQ-DRAFT.md         Q1-Q6 ticked / single paste-ready FAQ issue
    evidence/                         v2 screenshot frames + capture manifest (README.md)

## Answers

Q1 `{"status":"ok"}` · Q2 200 · Q3 404 · Q4 Normal · Q5 VERDICT (test alert, no
changes) · Q6 A (month-end day+2 overflow → timedelta). Verbatim agent lines and
evidence pointers: ANSWERS.md.
