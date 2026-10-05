# Security Audit Brief — Order Tracker HW4

Scope: credentials handling, autonomous-agent authorization, network posture and alerting
integrity of the order-tracker observability + incident-response stack, as operated on
2026-10-04/05. Method: live drill (8 incidents), log review (grafana `ngalert`, responder
uvicorn, copilot process logs), configuration review (compose, provisioning, autonomy policy).

## Findings summary

| ID | Title | Severity | Status |
|---|---|---|---|
| F-01 | PAT leaked via terminal screenshot | high | mitigated (revoked, rotated, playbook) |
| F-02 | Bridge-netns egress refused by corporate proxy → responder on host network | medium | accepted, documented |
| F-03 | Plaintext OAuth store in container (no keyring) | medium | accepted with mitigations |
| F-04 | Evaluator build failure masked as Normal (`execErrState: OK`) | medium | process fix (ngalert check) |
| F-05 | Missing `no_proxy` in responder env → proxy detours, evidence timeout, false 000s | medium | fixed, re-verified |

Details and dispositions: ../docs/operations-and-security-report.md §5.
Credential lifecycle playbook: credentials-handling.md.
Machine-readable records: findings per `findings.schema.json`, audit runs under `runs/`.

## Authorization model (capability summary)

See capability-table.md. Core invariant: the coding agent holds **Copilot inference +
local file edit + app rebuild/restart** capabilities only; storage, topology, credentials
and git history remain human-controlled. Every launch requires credentials present
(token or mounted store) and every firing alert persists an immutable incident record.

## Residual risk

- Plaintext OAuth store at rest (bounded by host disk permissions; rotate post-course).
- Responder on host network widens lateral reach (bounded by autonomy policy + no shell
  exposure; docker socket mounted rw is the accepted core risk of self-healing).
- Repeat notifications can launch multiple agent runs before silence (mitigation: silence
  after verified recovery; policy escalation forbids second changes).
