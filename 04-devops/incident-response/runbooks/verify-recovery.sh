#!/usr/bin/env bash
# verify-recovery.sh — exit 0 means the app is serving clean again.
# Run from anywhere inside the compose network (responder container).
set -uo pipefail
fail=0

code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 http://localhost:8000/healthz)
echo "healthz: $code"; [ "$code" = "200" ] || fail=1

# the previously-failing express order must now return 200
code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 http://localhost:8000/api/orders/express-1002)
echo "express-1002: $code"; [ "$code" = "200" ] || fail=1

# no 5xx in the last 2 minutes
fivexx=$(curl -s -G http://localhost:9090/api/v1/query \
  --data-urlencode 'query=sum(rate(http_server_requests_total{http_status_code=~"5.."}[2m])) or vector(0)' \
  | jq -r '.data.result[0].value[1] // "0"')
echo "5xx rate(2m): $fivexx"
awk -v v="$fivexx" 'BEGIN{exit !(v+0 == 0)}' || fail=1

if [ "$fail" = 0 ]; then echo "RECOVERY VERIFIED"; else echo "RECOVERY NOT VERIFIED"; fi
exit $fail
