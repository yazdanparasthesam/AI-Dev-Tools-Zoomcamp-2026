# Agent Relay — runtime image (Step 3, Q3)
# Single stage; uv installed from PyPI; reproducible installs from uv.lock.
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv

WORKDIR /app

# uv from PyPI, not from ghcr.io: the official uv image lives on ghcr.io,
# which is unreachable from some networks (build fails with
# "DeadlineExceeded ... ghcr.io/v2 ... i/o timeout" while docker.io pulls fine).
# PyPI is the registry this build already trusts for every other package.
RUN pip install --no-cache-dir 'uv>=0.9'

# Dependencies first: layer cache survives code edits
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev

# Application code
COPY main.py database.py storage.py schemas.py errors.py dashboard.py worker.py ./
COPY dashboard.html ./

EXPOSE 8000

# --host 0.0.0.0 is mandatory: uvicorn defaults to 127.0.0.1, which makes
# `docker run -p …` look broken from the host (homework tip, learned once).
CMD ["uv", "run", "--no-sync", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
