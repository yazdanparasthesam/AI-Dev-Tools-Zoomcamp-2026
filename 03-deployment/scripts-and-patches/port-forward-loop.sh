#!/usr/bin/env bash
# Pitfall #11: kubectl port-forward pins ONE endpoint pod; every rollout
# terminates that pod and the forward exits. This wrapper self-heals.
while true; do
  kubectl port-forward svc/app 8000:8000
  echo "[port-forward-loop] forward died (rollout?), restarting in 1s"
  sleep 1
done
