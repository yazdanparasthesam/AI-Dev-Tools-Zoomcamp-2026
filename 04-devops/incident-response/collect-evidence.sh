#!/usr/bin/env bash
# collect-evidence.sh <incident-dir> <target-string> <since-seconds>
# Pulls the three signals for a firing 5xx alert into the incident dir.
# Responder runs with network_mode: host => all backends via published 127.0.0.1 ports.
# v2: label/TraceQL based queries (body text rarely contains the route), so the
#     evidence is non-empty even when the alert annotation carries a template.
set -uo pipefail
DIR="${1:?incident dir}"; TARGET="${2:-order}"; SINCE="${3:-900}"
NOW=$(date +%s); START=$((NOW - SINCE))
mkdir -p "$DIR"

# logs: every 5xx-handling log record (http_status label promoted by collector hints)
curl -sf -G http://localhost:3100/loki/api/v1/query_range \
  --data-urlencode 'query={service_name="order-tracker", http_status=~"5.."}' \
  --data-urlencode "start=${START}" --data-urlencode "end=${NOW}" --data-urlencode "limit=200" \
  > "${DIR}/evidence-logs.json" \
  || curl -sf -G http://localhost:3100/loki/api/v1/query_range \
       --data-urlencode "query={service_name=\"order-tracker\"} |= \"${TARGET}\"" \
       --data-urlencode "start=${START}" --data-urlencode "end=${NOW}" --data-urlencode "limit=200" \
       > "${DIR}/evidence-logs.json" \
  || echo '{"status":"error","note":"loki query failed"}' > "${DIR}/evidence-logs.json"

# traces: TraceQL for server spans with 5xx status in the window
curl -sf -G http://localhost:3200/api/search \
  --data-urlencode 'q={resource.service.name="order-tracker" && span.http.status_code >= 500}' \
  --data-urlencode "start=${START}" --data-urlencode "end=${NOW}" --data-urlencode "limit=20" \
  > "${DIR}/evidence-traces.json" \
  || echo '{"status":"error","note":"tempo query failed"}' > "${DIR}/evidence-traces.json"

# metrics: 5xx increase per route+status over 10m
curl -sf -G http://localhost:9090/api/v1/query \
  --data-urlencode 'query=sum by (http_route,http_status_code)(increase(http_server_requests_total{http_status_code=~"5.."}[10m]))' \
  > "${DIR}/evidence-metrics.json" \
  || echo '{"status":"error","note":"prometheus query failed"}' > "${DIR}/evidence-metrics.json"

ls -1 "${DIR}"/evidence-*.json
