#!/usr/bin/env bash
# One-shot environment setup. Safe to re-run: it only installs what is missing.
#
#   ./scripts/setup.sh
#
# Useful after a fresh clone, and after anything that wipes untracked
# directories (.venv and node_modules are not committed).
set -euo pipefail

cd "$(dirname "$0")/.."

echo "==> uv"
if ! command -v uv >/dev/null 2>&1 && [ ! -x "$HOME/.local/bin/uv" ]; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
fi
export PATH="$HOME/.local/bin:$PATH"
uv --version

echo "==> Python dependencies"
if [ ! -d .venv ]; then
  uv sync
else
  echo "    .venv already present (run 'uv sync' to refresh)"
fi

echo "==> Node dependencies"
if [ ! -d frontend/node_modules ]; then
  (cd frontend && npm install)
else
  echo "    node_modules already present (run 'npm install' to refresh)"
fi

echo "==> Versions"
node -v
npm -v

cat <<'NEXT'

Setup complete. Start the app in two terminals:

  Terminal 1 (backend,  http://localhost:8000):
    make run-backend

  Terminal 2 (frontend, http://localhost:5173):
    make run-frontend

Then verify:

    make test
NEXT
