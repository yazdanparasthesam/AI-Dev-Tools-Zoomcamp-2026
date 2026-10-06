# Operations & Security Report — Order Tracker HW4 (DataTalksClub AI Dev Tools Zoomcamp 2026)

Operator: yazadanparast · Host: RMT-YZPARAST-UBT (Ubuntu) ·
Date of run: 2026-10-04 → 2026-10-05 · Stack: FastAPI+SQLite app, OTel Collector, Prometheus,
Loki, Tempo, Grafana 11.2.2, incident-responder (FastAPI :8001) with headless GitHub Copilot CLI 1.0.91.

Principle honoured throughout: **the model reasons; the system observes, authorizes, verifies
and remembers.** Every autonomous action below was gated by `incident-response/autonomy-policy.yaml`,
recorded under `incident-response/incidents/<id>/`, and verified by an independent script.

## 1. Answers (all live-confirmed)

| Q | Answer | Evidence |
|---|---|---|
| 1 | `{"status":"ok"}` | evidence/01-step1-build-up-healthz.png |
| 2 | `200` | evidence/06, 07 (curl -i 200 OK + console metric with route+status) |
| 3 | `404` | evidence/15, 20 (dashboard route×status table row `/api/orders/standard-1002 → 404`) |
| 4 | `Normal` | evidence/22 (rule state Normal, health ok, after 404 re-run; noDataState=OK) |
| 5 | free text: `VERDICT: Test alert required no changes; the app is healthy and the health endpoint returned HTTP 200 via localhost.` | evidence/39, 40; incident 20261005-103931-5db41b |
| 6 | **A** — express delivery estimate adds 2 to the day-of-month (`replace(day=…+2)`), which overflows at month-end; fixed with `timedelta(days=2)` | evidence/48; incident 20261005-175355-60e937; agent's own VERDICT |

## 2. Architecture

```
 curl / Grafana alerts
        │
        ▼
 ┌────────────┐  OTLP/HTTP :4318   ┌──────────────────┐
 │  app :8000 │ ─────────────────► │ otel-collector    │
 │ FastAPI +  │                    │  metrics ──► prometheus :9090 (scrape :8889)
 │ OTel mw    │                    │  logs    ──► loki :3100
 └────────────┘                    │  traces  ──► tempo :3200
        ▲                          └──────────────────┘
        │ rebuild/restart (docker socket)        │ alert rule 5xx (30s eval, for 1m)
 ┌──────┴─────────────────────────┐              ▼
 │ incident-responder :8001       │ ◄── webhook ─ grafana :3000
 │  POST /alerts → evidence →     │   (host.docker.internal, responder on host net)
 │  Copilot CLI headless (policy) │
 └────────────────────────────────┘
```

## 3. Incident reconstruction (by ID)

| Incident | Trigger | Policy decision | Agent action | Outcome |
|---|---|---|---|---|
| 20261005-090510-f9bbb3 | manual test POST (test=true) | observe-only; **launch blocked: no credentials** (autonomy gate) | none | skipped — gate evidence |
| 20261005-095623-4eb4b9 | manual test POST | observe-only; launched | copilot silent exit 1 | availability failure: bridge egress refused by corporate proxy (F-02 root cause) |
| 20261005-100910-09282e | manual test POST | observe-only; **launch blocked** (gate still token-only after OAuth-store mount) | none | responder bug, patched in 5c |
| 20261005-101417-46376c | manual test POST | observe-only; launched | silent exit 1 (ro store, sqlite WAL) | mount made writable |
| 20261005-103105-1d2ae6 | manual test POST | observe-only; launched | "No authentication information found" (host keyring vault) | login moved into container |
| 20261005-103931-5db41b | manual test POST (Q5) | observe-only (test=true) | health check only, no changes; 0.4 credits, 36 s | **Q5 VERDICT** captured |
| 20261005-175355-60e937 | **Grafana webhook, rule FIRING** (Q6) | diagnose-and-fix-within-policy | evidence (collector timed out, F-05) → root cause month-end `replace(day=…+2)` → patch `app/main.py` (+1 −1, `timedelta(days=2)`) → `docker build` → `compose up app` → verify-recovery; 1.12 credits, 8 m 50 s | **RECOVERY VERIFIED** (200/200/5xx=0); express-1002 `estimated_delivery 2026-10-02` |
| 20261005-180454-47d5ce | repeat notification while Firing | observe/escalate (fix already applied) | verification pass, no second change | policy escalation path exercised |

Model & configuration for every agent run: `github-copilot-cli` 1.0.91, headless
`copilot -p <rendered responder-task.md> --allow-all-tools`, cwd `/repo`, auth `oauth-store`
(container-local login, plaintext config fallback in mounted `~/.copilot`, see
security-audit/credentials-handling.md), timeout 900 s, prompt template
`incident-response/responder-task.md`, bounded by `autonomy-policy.yaml`
(may edit `app/*.py`, rebuild, restart; may not touch volumes/topology/credentials/git).

## 4. Alert lifecycle & the masked-evaluator episode

Rule `order-5xx-rate`: `sum(rate(http_server_requests_total{http_status_code=~"5.."}[5m]))`,
reduce-last → threshold >0, 30 s interval, `for: 1m`, `noDataState: OK` (quiet periods ⇒
**Normal**, Q4). After the Q3/Q4 evidence the rule silently failed to evaluate for ~1 h:
`reduce` lacked `expression: A`, then `threshold` lacked `expression: B`; the scheduler logged
`Failed to build rule evaluator` every tick while the UI showed green **Normal**
(`execErrState: OK` masks build errors). Detection: `docker compose logs grafana | grep ngalert`.
After both fixes: Pending (≈30 s) → **Firing** (≈90 s) → webhook → incident …-60e937 → fix →
window clears → **Normal**. Lesson codified as pitfall #7: provisioned alerting needs a
post-deploy *evaluation* assertion, not a health badge.

## 5. Security findings & dispositions

| ID | Finding | Severity | Disposition |
|---|---|---|---|
| F-01 | Fine-grained PAT exposed in a terminal screenshot mid-step | high | revoked+rotated immediately; exposing frames excluded from evidence & kit; credentials playbook written (security-audit/credentials-handling.md) |
| F-02 | Corporate proxy refuses TCP from compose bridge netns; responder moved to `network_mode: host` | medium | accepted trade-off, documented; agent reach bounded by autonomy policy |
| F-03 | Copilot OAuth token stored plaintext in mounted `~/.copilot` (no keyring in container) | medium | accepted with mitigations (owner-only dir, mounted store, rotation after course); alternative (token env) kept supported |
| F-04 | `execErrState: OK` masked a broken rule evaluator as Normal for ~1 h | medium | pitfall #7 + ngalert-log check added to deploy checklist |
| F-05 | `no_proxy` missing from responder env ⇒ in-stack curls detoured via proxy; evidence collector timed out (120 s), verify-recovery forged 000s | medium | compose env patched; verify re-run green (RECOVERY VERIFIED) |

## 6. Pitfalls catalogue (runbook §Pitfalls)

#1 compose walk-up to stale parent compose · #2 bridge DNS dead in build RUN ·
#3 zips/staging dirs left in repo · #4 sudo strips env (`.env` channel) ·
#5 bridge egress refused (host net) · #6 keyring vault vs container store ·
#7 expression nodes need explicit `expression:` inputs; execErrState masks build errors ·
#8 rate() measures change inside the window · #9 proxy env without no_proxy.

## 7. Verification artefacts

`verify-recovery.sh` (healthz 200, express-1002 200, 5xx rate(2m)=0 ⇒ RECOVERY VERIFIED,
evidence/51) · dashboard frames 15/20/46 · rule states 22/45 · agent outputs in
`incident-response/incidents/*/agent-output.txt` · response records conform to
`incident-response/response.schema.json`.

## 8. Residual / optional

Loki/Tempo Explore screenshots (pipeline already proven via dashboard+collector) and the two
closing commits (`fix(orders): …timedelta…`, `feat(observability+incident-response): …`) are
operator-side actions recorded in the submission checklist, not open technical items.

**F-06** — malformed webhook JSON crashed `/alerts` with a 500; responder now validates the body and answers 400 (low, fixed).
### 3.9 Incident 20261005-225517-e6be87 (v2 Q5 re-run)
Test notification (`test: true`) over the token channel; observe-only policy;
agent `github-copilot-cli` completed in 37 s with `VERDICT: Synthetic test
alert; no changes made, and app health verified with HTTP 200.`

### 3.10 Incident 20261005-235349-fe18ef (v2 Q6 drill)
Chaos-injected month-end bug (T6-9 drill injection) → rule Firing → webhook →
evidence collected **true** (first proxy-free run, F-05 closed) → agent
re-applied the timedelta fix, rebuilt, restarted, verified: `VERDICT:
Month-end date replacement caused express-order 500s; rebuilt and restarted
with the existing timedelta fix, and recovery verification passed (healthz
200, order lookup 200, 5xx rate 0).`

