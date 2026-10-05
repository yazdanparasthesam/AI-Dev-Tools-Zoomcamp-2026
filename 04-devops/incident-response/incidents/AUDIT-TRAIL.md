# Incident audit trail (2026-10-05)

Raw per-incident records (alert.json, task.md, evidence-*.json, agent-output.txt,
response.json) live in this directory on the operator's clone; the table below is
the committed summary. Full reconstruction: ../../docs/operations-and-security-report.md §3.

| Incident | Trigger | Decision | Agent | Outcome |
|---|---|---|---|---|
| 20261005-090510-f9bbb3 | manual test POST | observe-only; launch blocked (no credentials) | none | policy-gate evidence |
| 20261005-095623-4eb4b9 | manual test POST | observe-only; launched | silent exit 1 | bridge egress refused (F-02) |
| 20261005-100910-09282e | manual test POST | observe-only; launch blocked (token-only gate v1) | none | responder patched (5c) |
| 20261005-101417-46376c | manual test POST | observe-only; launched | silent exit 1 | ro OAuth store (sqlite WAL) |
| 20261005-103105-1d2ae6 | manual test POST | observe-only; launched | no-auth-info | keyring vault (T5-6) |
| 20261005-103931-5db41b | manual test POST (Q5) | observe-only (test=true) | health check, no changes | Q5 VERDICT captured |
| 20261005-175355-60e937 | Grafana webhook FIRING (Q6) | diagnose-and-fix-within-policy | timedelta patch +1 −1, rebuild, restart, verify | RECOVERY VERIFIED |
| 20261005-180454-47d5ce | repeat notification | observe/escalate (fix applied) | verification only | escalation path exercised |
