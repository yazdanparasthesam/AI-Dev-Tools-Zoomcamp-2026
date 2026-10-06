# HW4 answers — Order Tracker (module 04)

Status: predictions derived from reading the starter code; each is confirmed
(or corrected) by a live run before submission. Deadline 2026-10-06 02:30.

- [x] Q1 `{"status":"ok"}` — confirmed live 2026-10-04: container Healthy,
      curl body `{"status":"ok"}` (hw4-images/01).
[x] Q2 `200` — CONFIRMED live 2026-10-04: curl -i → 200 OK and the console
      metric http.server.requests carries http.route + http.status_code
      (hw4-images/06-07). Original prediction — `standard-1001` is seeded, lookup succeeds; metric attribute
      `http.status_code` = 200 in `docker compose logs app`.
[x] Q3 `404` — CONFIRMED live 2026-10-05 (dashboard route×status table row;
      Loki/Tempo frames still to archive). Original prediction — — `standard-1002` is NOT seeded ⇒ HTTPException(404); the same
      code appears on the metric in Grafana (Prometheus), with matching log
      (Loki) and trace (Tempo).
[x] Q4 `Normal` — CONFIRMED live 2026-10-05 (rule state Normal, health ok,
      after 404 re-run; noDataState=OK handles 5xx-quiet periods). Original prediction — — 404s are not 5xx; with no-data handled (noDataState OK)
      the alert evaluates to Normal until a real 5xx lands.
[x] Q5 — CONFIRMED live 2026-10-05. Agent last line (verbatim):
      "VERDICT: Synthetic test alert; no changes made, and app health verified with HTTP 200." (incident 20261005-225517-e6be87 (v2 re-run; morning run 20261005-225517-e6be87 (v2 re-run; morning run 20261005-103931-5db41b superseded) superseded),
      Copilot CLI 1.0.91 headless, auth=oauth-store, observe-only per policy).
      Original free-text placeholder — free text — responder's headless-agent reply to the test alert;
      paste the agent's last line verbatim.
[x] Q6 **A** — CONFIRMED live 2026-10-05 by the headless agent itself:
      "VERDICT: Month-end date replacement caused express-order 500s; rebuilt and restarted with the existing timedelta fix, and recovery verification passed (healthz 200, order lookup 200, 5xx rate 0)." (incident 20261005-235349-fe18ef (v2 drill; morning incident 20261005-235349-fe18ef (v2 drill; morning incident 20261005-175355-60e937 superseded) superseded)).
      Original prediction — option A — "The express delivery date calculation tried to use a day
      that does not exist in that month." (`replace(day=day+2)` on month-end
      seeded order ⇒ ValueError ⇒ 500; fix = `timedelta(days=2)`.)
