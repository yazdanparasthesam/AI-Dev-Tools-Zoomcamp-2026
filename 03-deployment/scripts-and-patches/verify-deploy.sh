#!/usr/bin/env bash
# Post-deploy verification pair (steps 5 & 6b/6c): what heading is live, and
# which image tag is the Deployment actually running.
set -euo pipefail
echo -n "live heading: "; curl -s localhost:8000 | grep -o '<h1>[^<]*</h1>' || echo "(nothing on :8000 - is the forward up?)"
echo -n "live image:   "; kubectl get deployment app -o jsonpath='{.spec.template.spec.containers[0].image}'; echo
