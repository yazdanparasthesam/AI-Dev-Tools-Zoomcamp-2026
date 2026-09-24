#!/usr/bin/env bash
# Run the FULL ci workflow (test job + gated deploy to local kind) with act.
# Prereqs: docker daemon up, kind cluster named "relay" up, sudo rights.
# Pitfalls encoded here: services resolve by NAME under act (--var DB_HOST),
# no_proxy keeps curl/httpx off the proxy for loopback targets (runbook #6).
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
sudo act push -W .github/workflows/ci.yml -P ubuntu-latest=ubuntu:22.04 \
  --var DEPLOY_TARGET=kind-local --var DB_HOST=postgres \
  --env no_proxy=localhost,127.0.0.1,postgres \
  --env NO_PROXY=localhost,127.0.0.1,postgres
