# Credentials Playbook — GitHub Copilot CLI for a Headless Incident Responder

Scope: how the order-tracker incident responder authenticates its headless
coding agent (GitHub Copilot CLI 1.0.x), how the credential is created,
stored, injected, rotated and audited. Written as an operational document:
every statement below was exercised live on the homework stack (see
`HW4-RUNBOOK.md` Step 5 and `incident-response/incidents/`).

Principle: **the model reasons; the system observes, authorizes, verifies and
remembers.** A credential is an authorization artifact — it must be created
with least privilege, stored out of sight, injected through a channel that
survives `sudo`, verified before use, and rotated the moment it leaks.

---

## 1. What Copilot CLI accepts as authentication

| Method | How obtained | Where it lives | Headless-friendly? |
|---|---|---|---|
| OAuth device flow | `copilot login` → browser approve | Desktop: **session keyring**; keyring-less host: plaintext config after explicit `y` consent | Yes, once the store exists |
| Fine-grained PAT | GitHub UI (§2) | Whatever file/env you put it in | Yes — env var |
| Classic PAT | GitHub UI (legacy) | Same | Yes — env var |
| `gh auth login` | GitHub CLI | `~/.config/gh/hosts.yml` | Yes; copilot reads it |
| Env vars | `COPILOT_GITHUB_TOKEN`, `GH_TOKEN`, `GITHUB_TOKEN` | process env | Yes — the CI-standard path |

Environment variables the CLI honors, in order of precedence:
`COPILOT_GITHUB_TOKEN` → `GH_TOKEN` → `GITHUB_TOKEN`, then the OAuth store,
then `gh`'s store.

## 2. Creating a fine-grained PAT with the right access (step by step)

1. GitHub → **Settings** (avatar menu) → **Developer settings** (left sidebar,
   bottom) → **Personal access tokens** → **Fine-grained tokens** →
   **Generate new token**.
2. **Token name**: `copilot-cli-responder-hw4`. **Expiration**: ≤ 7 days for
   homework-grade credentials; never "No expiration".
3. **Repository access**: *Only select repositories* → your order-tracker
   fork. Least privilege: the agent works in that repo only.
4. **Permissions** — the part everyone misses:
   - *Repository permissions* → **Copilot requests: Read** (without it the
     Copilot API answers 403 "forbidden: access denied"; the CLI surfaces this
     as "Access denied by policy settings").
   - *Repository permissions* → **Contents: Read and write** only if you want
     the token itself (not just the local agent) to touch repo content.
   - Everything else: **No access**.
5. For an org-owned account, an administrator must also allow Copilot for the
   account/organization (`https://github.com/settings/copilot` and org
   policies) — otherwise even a perfect token hits the policy gate.
6. **Generate**, then copy the value **once**, immediately into a file
   (§3). The UI never shows it again.

Diagnostics table (observed live, in order of encounter):

| Symptom | Meaning |
|---|---|
| `401 Bad credentials` on `/user` | token string invalid/expired/revoked — re-copy or re-mint; verify with §6 before use |
| `403 forbidden: access denied` from `copilot_internal/*` | valid token, missing **Copilot requests** permission or plan/org policy |
| `Access denied by policy settings` | account/plan/org gate (or the missing permission above) |
| `No authentication information found` | no token env var **and** no readable OAuth store (typical inside containers: no keyring) |
| `network fetch failed` | egress problem (proxy/ACL/TLS), not an auth problem |

## 3. Storage on the operator machine

```bash
umask 077                       # new files: owner-only from birth
nano ~/.copilot-token           # paste once; Ctrl-O Enter, Ctrl-X
chmod 600 ~/.copilot-token      # belt and braces
export COPILOT_GITHUB_TOKEN=$(cat ~/.copilot-token)   # shell never sees it in history
```

Rules enforced in this project:

- **Never** type the token into a command line (shell history), a screenshot,
  a chat message, a commit, or an image embedded in documentation.
- **Never** store it in the repo. The repo carries only the *mechanism*
  (`.gitignore` entries, compose variable references), never the secret.
- Read it with `$(cat …)` or `read -s`; verify without displaying:
  `printenv COPILOT_GITHUB_TOKEN | cut -c1-10`.

## 4. The `.env` file and compose interpolation — why it exists

`compose.yaml` references the secret as `COPILOT_GITHUB_TOKEN:
${COPILOT_GITHUB_TOKEN:-}`. Compose resolves `${VAR}` from (a) the shell
environment of the compose process, then (b) a **`.env` file in the project
directory**. This project runs compose under `sudo`, and **sudo strips the
caller's environment** — an exported token silently interpolates to empty and
the container is created credential-less (incident `20261005-090510-f9bbb3`
records the policy gate catching exactly that). The `.env` file is immune to
this because it is read from disk, not from the environment:

```bash
grep -qxF '.env' .gitignore || echo '.env' >> .gitignore   # ignore first, always
printf 'COPILOT_GITHUB_TOKEN=%s\n' "$COPILOT_GITHUB_TOKEN" > .env
sudo docker compose up -d --wait        # container now receives the token
```

The same `.env` also carries `http_proxy`/`https_proxy`/`no_proxy` for the
same sudo-proof reason; `no_proxy` must list every compose service name or
in-stack HTTP calls detour through the corporate proxy and die.

Verify the channel: `git check-ignore -v .env` (must print a rule),
`sudo docker compose exec incident-responder printenv COPILOT_GITHUB_TOKEN |
cut -c1-10` (must print the token prefix), and `git log --oneline -- .env`
(must be empty).

## 5. Inside the container: two vaults and their trade-offs

- **Token path** — compose `environment:` injects `COPILOT_GITHUB_TOKEN`;
  simplest, revocable by editing `.env` + recreate.
- **OAuth-store path** (the one in production here) — `copilot login` is run
  *inside the responder container*; with no keyring available the CLI asks
  `Store token in plaintext config file? (y/N)` and writes its store to
  `/root/.copilot`, which compose bind-mounts from the host
  (`/home/<user>/.copilot:/root/.copilot`, **writable** — the session DB is a
  SQLite WAL and refuses read-only mounts). The device-flow callback works
  because the responder uses `network_mode: host`, so the CLI's localhost
  callback port is reachable from the host browser.

Trade-offs accepted and documented: plaintext-at-rest store (mitigated by
owner-only directory permissions and host-side disk encryption), writable
mount (required by WAL), host networking (required by corporate proxy ACLs).
All three are bounded by `incident-response/autonomy-policy.yaml`, which
forbids the agent from reading/exporting credentials, pushing to git, or
touching topology — the credential authorizes *Copilot inference*, not
repository or infrastructure control.

## 6. Verify-before-use checklist (kills whole bug classes early)

```bash
T=$(cat ~/.copilot-token)
curl -s -H "Authorization: Bearer $T" https://api.github.com/user | head -2   # login name ⇒ token alive
COPILOT_GITHUB_TOKEN=$T copilot -p "Reply with exactly one word: PONG"        # PONG ⇒ Copilot API authorized
unset T
```

Only after both pass may the value enter `.env` or any container.

## 7. Rotation & revocation playbook (leak = screenshot, chat, commit, log)

1. GitHub → Settings → Developer settings → Personal access tokens →
   **delete the leaked token immediately** (revocation is instant).
2. Mint a replacement per §2; run §6 against it.
3. Rewrite `~/.copilot-token` and `.env`; `sudo docker compose up -d --wait`
   (containers keep the old value until recreated).
4. Purge the leak artifact from documentation/evidence; if it ever reached a
   commit, treat history as poisoned (`git filter-repo`) or rotate again.
5. Record the event in the incident trail — this project's burned-PAT event
   is documented in `HW4-RUNBOOK.md` (security note, Step 5) and in the final
   operations-and-security report; the exposing screenshot was never archived.

## 8. Audit trail anchor

Every authorization decision the responder made is persisted under
`incident-response/incidents/<id>/` (`alert.json`, `task.md`,
`agent-output.txt`, `response.json` conforming to `response.schema.json`):
skipped-without-credential, launched-without-egress, completed-observe-only,
completed-with-fix. The credential story above is therefore not prose but a
replayable record — which is the point of the whole module.
