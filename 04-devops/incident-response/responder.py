"""Incident responder — receives Grafana alert webhooks on :8001.

For every firing alert it:
  1. stores the raw payload under incident-response/incidents/<id>/alert.json
  2. collects logs/traces/metrics evidence (collect-evidence.sh) unless test mode
  3. launches the coding assistant (GitHub Copilot CLI) headless with
     responder-task.md as the prompt, gated by COPILOT_GITHUB_TOKEN and
     bounded by autonomy-policy.yaml
  4. writes response.json (see response.schema.json) with the agent's last line
"""
import json
import os
import shutil
import subprocess
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

REPO = Path(os.environ.get("REPO_DIR", "/repo"))
INCIDENTS = Path(os.environ.get("INCIDENTS_DIR", str(REPO / "incident-response" / "incidents")))
TASK_TEMPLATE = Path(__file__).parent / "responder-task.md"
AGENT_TIMEOUT = int(os.environ.get("AGENT_TIMEOUT", "900"))

app = FastAPI(title="incident-responder", version="1.0.0")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


@app.get("/incidents")
async def list_incidents():
    ids = sorted(p.name for p in INCIDENTS.iterdir() if p.is_dir()) if INCIDENTS.exists() else []
    return {"incidents": ids}


@app.get("/incidents/{incident_id}")
async def get_incident(incident_id: str):
    f = INCIDENTS / incident_id / "response.json"
    if not f.exists():
        return JSONResponse({"detail": "not found"}, status_code=404)
    return json.loads(f.read_text())


def collect_evidence(incident_dir: Path, target: str) -> dict:
    script = Path(__file__).parent / "collect-evidence.sh"
    try:
        proc = subprocess.run(
            ["bash", str(script), str(incident_dir), target, "900"],
            capture_output=True, text=True, timeout=120,
        )
        return {
            "collected": proc.returncode == 0,
            "logs": str(incident_dir / "evidence-logs.json"),
            "traces": str(incident_dir / "evidence-traces.json"),
            "metrics": str(incident_dir / "evidence-metrics.json"),
            "stderr": proc.stderr[-500:] if proc.stderr else "",
        }
    except Exception as exc:  # noqa: BLE001
        return {"collected": False, "error": str(exc)}


def _copilot_credentials() -> str:
    """Return how copilot can authenticate: 'token', 'oauth-store', or ''."""
    if os.environ.get("COPILOT_GITHUB_TOKEN", ""):
        return "token"
    home = Path(os.environ.get("HOME", "/root"))
    stores = [home / ".copilot", home / ".config" / "github-copilot",
              Path("/root/.copilot"), Path("/root/.config/github-copilot")]
    names = ("config.json", "hosts.yml", "session-store.db")
    for store in stores:
        if any((store / n).exists() for n in names):
            return "oauth-store"
    return ""


def launch_agent(incident_dir: Path, incident_id: str, test_mode: bool, endpoint: str) -> dict:
    if not shutil.which("copilot"):
        return {"status": "skipped", "reason": "copilot CLI not installed in container"}
    auth = _copilot_credentials()
    if not auth:
        return {"status": "skipped",
                "reason": "no Copilot credentials (COPILOT_GITHUB_TOKEN or mounted OAuth store) — policy: no authorization, no autonomous agent"}
    prompt = TASK_TEMPLATE.read_text()
    prompt = (prompt.replace("{incident_id}", incident_id)
                    .replace("{incident_dir}", str(incident_dir))
                    .replace("{test_mode}", "true" if test_mode else "false")
                    .replace("{endpoint}", endpoint))
    (incident_dir / "task.md").write_text(prompt)
    cmd = ["copilot", "-p", prompt, "--allow-all-tools"]
    started = _now()
    try:
        proc = subprocess.run(
            cmd, cwd=str(REPO), capture_output=True, text=True,
            timeout=AGENT_TIMEOUT, stdin=subprocess.DEVNULL,
            env=dict(os.environ),
        )
        out = proc.stdout or ""
        (incident_dir / "agent-output.txt").write_text(out + proc.stderr)
        lines = [ln.strip() for ln in out.splitlines() if ln.strip()]
        return {
            "status": "completed",
            "model": "github-copilot-cli",
            "auth": auth,
            "command": " ".join(cmd[:2]) + " <task.md prompt> --allow-all-tools",
            "exit_code": proc.returncode,
            "started_at": started,
            "finished_at": _now(),
            "last_line": lines[-1] if lines else "(no output)",
        }
    except subprocess.TimeoutExpired:
        return {"status": "timeout", "model": "github-copilot-cli", "last_line": "(agent timed out)"}
    except Exception as exc:  # noqa: BLE001
        return {"status": "error", "model": "github-copilot-cli", "last_line": f"(agent error: {exc})"}


@app.post("/alerts")
async def alerts(request: Request):
    try:
        payload = await request.json()
    except Exception:  # malformed body: reject cleanly instead of a 500
        return JSONResponse({"error": "invalid JSON body"}, status_code=400)
    if not isinstance(payload, dict):
        return JSONResponse({"error": "alert payload must be a JSON object"},
                            status_code=400)
    incident_id = time.strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:6]
    incident_dir = INCIDENTS / incident_id
    incident_dir.mkdir(parents=True, exist_ok=True)
    (incident_dir / "alert.json").write_text(json.dumps(payload, indent=2))

    alert_list = payload.get("alerts", []) or []
    firing = [a for a in alert_list if a.get("status") == "firing"]
    labels0 = (alert_list[0] or {}).get("labels", {}) if alert_list else {}
    annotations0 = (alert_list[0] or {}).get("annotations", {}) if alert_list else {}
    test_mode = (
        payload.get("test") is True
        or labels0.get("test") == "true"
        or "no incident to fix" in annotations0.get("summary", "").lower()
    )
    endpoint = annotations0.get("endpoint", labels0.get("alertname", "unknown"))

    evidence = {} if test_mode else collect_evidence(incident_dir, endpoint)
    agent = launch_agent(incident_dir, incident_id, test_mode, endpoint) if firing else {
        "status": "skipped", "reason": "no firing alerts in payload (resolved notification)"}

    record = {
        "incident_id": incident_id,
        "received_at": _now(),
        "alert": {
            "status": payload.get("status"),
            "alertname": labels0.get("alertname"),
            "labels": labels0,
            "annotations": annotations0,
            "endpoint": endpoint,
            "dashboard_url": annotations0.get("dashboard_url"),
        },
        "test_mode": test_mode,
        "evidence": evidence,
        "agent": agent,
        "policy": "incident-response/autonomy-policy.yaml",
        "decision": {
            "action": "observe-only" if test_mode else "diagnose-and-fix-within-policy",
            "reason": "test notification" if test_mode else "firing 5xx alert",
        },
    }
    (incident_dir / "response.json").write_text(json.dumps(record, indent=2))
    return JSONResponse({"incident_id": incident_id, "test_mode": test_mode,
                         "agent_last_line": agent.get("last_line")})
