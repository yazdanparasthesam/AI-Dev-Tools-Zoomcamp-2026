#!/usr/bin/env python3
"""Pitfall #10: stale credentials in ~/.docker/config.json made docker offer
Harbor-style auth to docker.io -> "denied: RBAC: access denied" on service
pulls (run 5, first attempt). Backs the file up and drops only credential
material (auths / credsStore / credentialHelpers), keeping proxies etc."""
import json, os
p = os.path.expanduser("~/.docker/config.json")
if not os.path.exists(p):
    print("no docker config.json - nothing to do"); raise SystemExit
shutil_bak = p + ".bak"
d = json.load(open(p))
for k in ("auths", "credsStore", "credentialHelpers"):
    d.pop(k, None)
os.replace(p, shutil_bak) if False else open(shutil_bak, "w").write(open(p).read())
json.dump(d, open(p, "w"), indent=2)
print("pruned; backup at", shutil_bak)
