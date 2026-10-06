# evidence/ — v2 capture manifest (proxy-free re-run)

Frames 01-05, 07-13 are already captured. Save each remaining frame under the
EXACT filename below as its step is re-run; RUNBOOK.md embeds and the 5.4/6.4
indexes resolve automatically. One logical step per frame, full terminal
window (prompt + command + complete output); browser frames include the URL
bar. Success path only — failures stay prose episodes in RUNBOOK.md.

| filename | should show |
|---|---|
| 01-step1-repo-tree.png | repo root listing: Dockerfile, app/, compose.yaml, observability/, incident-response/ present |
| 02-step1-build-finished.png | sudo docker build -t order-tracker:local . → (14/14) FINISHED, new image sha |
| 03-step1-up-healthy.png | sudo docker compose up -d --wait → Running 8/8, all seven containers Healthy |
| 04-step1-healthz-200.png | curl -i localhost:8000/healthz → 200 OK + {"status":"ok"} |
| 05-step1-compose-ps.png | sudo docker compose ps → seven services Up, app (healthy), published ports |
| 06-step2-git-status.png | git status --short: only the instrumented app files modified |
| 07-step2-console-run-curl200.png | ot-console on the instrumented image: curl -i standard-1001 → 200 + seeded JSON; sleep 8 for the 5s reader |
| 08-step2-metric-export.png | docker logs tail: resource_metrics — http.server.requests, http.method GET, http.route, http.status_code 200, value 1 |
| 09-step3-up-404-logs.png | continuous: compose up 8/8 Healthy + ps table + curl standard-1002 → 404 JSON + logs app plain uvicorn lines |
| 10-step3-dashboards-list.png | localhost:3000/dashboards: provisioned Order Tracker dashboard (tags hw4, order-tracker) + Order Tracker Alerts folder |
| 11-step3-dashboard-404.png | dashboard body: rate-by-route lines, 5xx panel flat 0, table row standard-1002 · 404 · 1.01 |
| 12-step4-rule-normal.png | Alert rules: order-tracker-5xx Provisioned, state Normal, health ok, Every 30s, pending 1m, labels + dashboard_url |
| 13-step4-rule-nodata-instance.png | rule detail: noDataState=OK in description, window 5m; Instances row Normal (Nodata) with alertname/folder labels |
| 14-step5-env-hygiene-tree.png | cat .env with PAT black-boxed + ll incident-response/ + sed command |
| 15-step5-responder-build.png | responder build 17/17 (layer 5/11 npm install -g @github/copilot) + up 8/8 Healthy |
| 16-step5-block-healthz.png | sed responder-block output + curl -i localhost:8001/healthz → 200 (continuous) |
| 17-step5-test-post.png | curl -i POST /alerts with test=true ResponderTest payload → accepted + incident id |
| 18-step5-response-verdict.png | cat incidents/<id>/response.json: agent completed + final VERDICT line (Q5 answer) |
| 19-step5-copilot-version.png | host: copilot --version (CLI installed, OAuth store mounted) |
| 20-step6-fullstack-restored.png | compose up -d --wait (no service arg) → 8/8 + ps seven services Healthy after T6-8 |
| 21-step6-bug-injection.png | sed revert of the timedelta fix + all-CACHED build + scoped up app; express → 500 |
| 22-step6-curl500-keeper.png | curl -i express-1002 → 500 + keeper backgrounded + jobs + sleep 120 |
| 23-step6-dashboard-5xx-live.png | 5xx panel ~0.04-0.05 req/s; table rows 200/200/500·20 (dup-keeper spike visible) |
| 24-step6-rule-firing.png | Alert rules: 1 firing, rule Firing for 7m, health ok, Provisioned |
| 25-step6-keeper-dup-kill.png | jobs shows loops [2]+[3]; kill %1 no such job; kill %2 terminates first |
| 26-step6-keeper-cleanup.png | kill %3 terminates second loop; jobs empty |
| 27-step6-response-verdict.png | response.json fe18ef: evidence collected true, agent completed auth token, VERDICT line (Q6 answer) |
| 28-step6-curl200-restored.png | curl -i express-1002 → 200 + estimated_delivery 2026-10-02 |
| 29-step6-verify-recovery.png | verify-recovery.sh inside responder: healthz 200 / express 200 / 5xx rate 0 / RECOVERY VERIFIED |
