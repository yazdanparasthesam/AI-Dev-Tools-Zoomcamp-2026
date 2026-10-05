# Capability Table — who may do what

| Capability | Coding agent (Copilot CLI) | Responder service | Human operator |
|---|---|---|---|
| Read alert payload + evidence | yes (task-bound) | yes | yes |
| Query Loki/Tempo/Prometheus | via evidence files + own curls | yes (collect-evidence.sh) | yes |
| Edit `app/*.py` (behavioural, no new deps) | **yes (auto, within policy)** | no | yes |
| Rebuild app image / restart app container | **yes (auto, house incantation)** | no | yes |
| Run verify-recovery.sh / rollback.sh | yes | yes | yes |
| Edit compose topology, ports, images of other services | **forbidden** | no | yes |
| Delete/recreate volumes or the orders DB | **forbidden** | no | yes (deliberate) |
| Read/export credentials, proxy passwords | **forbidden** | holds env/mount only | yes |
| git commit / push / open PRs | **forbidden** | no | **yes (sole owner of history)** |
| Launch further agents | no | yes (policy-gated) | yes |
| Silence/mute alerts | no | no | yes |

Enforcement points: `autonomy-policy.yaml` (prompt-level bound), responder gate
(credentials required), task template (explicit forbid list), docker socket scope
(single host), and post-hoc incident records (audit). Verification is never delegated:
`verify-recovery.sh` runs independently of the agent's own claims, and the operator
re-verifies with curl + UI frames.
