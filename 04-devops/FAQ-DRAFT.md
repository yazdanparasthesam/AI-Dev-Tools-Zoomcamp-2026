# FAQ proposal (single issue, paste-ready)

**Title:** HW4: provisioned Grafana alert rule stays Normal while 5xx are live — masked evaluator build error (reduce/threshold missing `expression:` input)

**Body:**

Symptom: `observability/alerts.yaml` provisioned rule (Prometheus query → reduce →
threshold) shows State **Normal**, Health **ok**, "Next evaluation in a few seconds",
while the dashboard panel for the very same expression (`sum(rate(http_server_requests_total{http_status_code=~"5.."}[5m]))`) clearly shows >0 and `/api/v1/query` returns a positive value. Re-firing the trigger and restarting Grafana do not help.

Cause: in Grafana 10/11 provisioning, **every expression node must declare its input
explicitly**: the `reduce` node needs `expression: <refId of the query>` and the
`threshold` node needs `expression: <refId of the reduce>` (the legacy
`conditions[].query.params` alone is not enough). Without them the scheduler fails
every tick with `Failed to build rule evaluator: failed to parse expression 'B': no
expression ID is specified to reduce` / `'C': no variable specified to reference`,
and because the rule sets `execErrState: OK` (a sensible choice to hide transient
query errors), the UI masks the broken evaluator as a healthy **Normal** — exactly
the state you'd expect during a quiet period.

Diagnosis (one command): `sudo docker compose logs grafana --since 10m | grep ngalert`
— the build error repeats every evaluation interval.

Fix:

```yaml
          - refId: B
            datasourceUid: __expr__
            model:
              refId: B
              type: reduce
              reducer: last
              expression: A        # ← input of the reduce
          - refId: C
            datasourceUid: __expr__
            model:
              refId: C
              type: threshold
              expression: B        # ← input of the threshold
              conditions:
                - evaluator: {type: gt, params: [0]}
                  operator: {type: and}
                  query: {params: ["B"]}
                  reducer: {type: last, params: []}
                  type: query
```

then `sudo docker compose restart grafana` (provisioning re-reads at boot). Pending
appears within one evaluation interval, Firing after `for:` elapses.

Prevention: after deploying provisioned alerting, assert *evaluation*, not health —
grep the `ngalert` scheduler log for `Failed to build rule evaluator`, or check the
rule's State history for real Ok/Alerting entries instead of `Normal (Error)`.

**Answer (for the FAQ page):** add `expression:` inputs to every reduce/threshold node
and verify via `ngalert` logs; `execErrState: OK` hides evaluator build failures behind
a green Normal badge.
