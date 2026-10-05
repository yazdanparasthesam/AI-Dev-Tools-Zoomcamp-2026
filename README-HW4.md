# HW4 — Order Tracker: observability + autonomous incident response

Drop this archive at the **root of your order-tracker fork** and commit: code and
configs merge over the live tree (identical content), the docs layer is new.

    unzip hw4-github-upload.zip -d /path/to/order-tracker
    cd /path/to/order-tracker && git add -A && git commit -m "docs(hw4): runbook, report, security audit, evidence" && git push

Layout:

    compose.yaml, observability/, incident-response/   final live configs & responder code
    incident-response/incidents/AUDIT-TRAIL.md         eight-incident summary (raw records on operator clone)
    RUNBOOK.md                                         step-by-step run, pitfalls #1-#9, T5-x/T6-x troubleshoot episodes
    ANSWERS.md                                         Q1-Q6, ticked with live-confirmation notes
    docs/operations-and-security-report.md             incident-by-ID reconstruction, findings F-01..F-05
    security-audit/                                    audit brief, findings schema, capability table, runs, credentials playbook
    evidence/                                          47 green-path frames (failures documented as prose in RUNBOOK.md)
    FAQ-DRAFT.md                                       single paste-ready FAQ issue (masked-evaluator story)

Answers: Q1 {"status":"ok"} · Q2 200 · Q3 404 · Q4 Normal · Q5 VERDICT (test alert,
no changes) · Q6 A (month-end day+2 overflow → timedelta). See ANSWERS.md for the
verbatim agent lines and evidence pointers.
