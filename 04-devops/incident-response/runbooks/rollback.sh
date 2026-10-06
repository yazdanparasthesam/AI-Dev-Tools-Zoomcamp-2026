#!/usr/bin/env bash
# rollback.sh — put app/ back to the last committed state and redeploy.
# Run from the responder container (docker socket + /repo mounted) or the host.
set -uo pipefail
REPO="${REPO_DIR:-/repo}"
git -C "$REPO" restore -- app/ || { echo "nothing to restore / git error"; exit 1; }
docker build -t order-tracker:local "$REPO" || exit 1
docker compose -f "$REPO/compose.yaml" up -d --wait app || exit 1
echo "ROLLED BACK to last committed app/"
