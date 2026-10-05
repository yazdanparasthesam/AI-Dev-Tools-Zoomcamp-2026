# Audit run 2026-10-05 — credentials rotation (F-01)

Trigger: fine-grained PAT visible in a terminal screenshot shared during Step 5.
Actions: token revoked at GitHub within minutes; replacement minted with
`Copilot requests: Read` on the single repository; stored at `~/.copilot-token`
(mode 600, umask 077) and injected via gitignored `.env`; exposing frames excluded
from `evidence/` and from the kit; playbook written (credentials-handling.md).
Verification: `git check-ignore -v .env` rule present; `git log -- .env` empty;
container env prefix check via `printenv | cut -c1-10`; host + in-container PONG.
Result: mitigated. Residual: none for the leaked value (revoked).

# Audit run 2026-10-05 — masked evaluator (F-04)

Trigger: rule badge Normal while dashboard showed live 5xx rate 0.05.
Detection: `docker compose logs grafana | grep ngalert` → repeated
`Failed to build rule evaluator: failed to parse expression 'B'/'C' …`.
Root cause: provisioned expression nodes missing input references
(`reduce` needs `expression: A`, `threshold` needs `expression: B`);
`execErrState: OK` rendered the build failure as a healthy Normal.
Fix: two-line `observability/alerts.yaml` patch + `compose restart grafana`.
Verification: Pending → Firing within 90 s of sustained 5xx; webhook delivered.
Result: fixed; deploy checklist now includes an evaluation assertion.

# Audit run 2026-10-05 — proxy detour / no_proxy gap (F-05)

Trigger: incident …-60e937 `evidence.collected: false … timed out after 120 seconds`;
`verify-recovery.sh` printed 000s from inside the responder while host curls returned 200.
Root cause: compose mapped `http_proxy`/`https_proxy` into the responder but not
`no_proxy`; in-stack `localhost:` curls detoured through the corporate proxy.
Fix: `no_proxy: ${no_proxy:-}` added to the service environment; recreate.
Verification: `verify-recovery.sh` → healthz 200 / express-1002 200 / 5xx 0 /
RECOVERY VERIFIED (evidence/51-step6-recovery-verified.png).
Result: fixed.
