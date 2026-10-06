# Incident responder image: python app + headless Copilot CLI + docker CLI
# (the agent may need to rebuild/restart the app container after a fix).
FROM node:20-bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl jq python3 python3-pip git ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# static docker CLI (socket is mounted read-write by compose)
RUN curl -fsSL https://download.docker.com/linux/static/stable/x86_64/docker-27.3.1.tgz \
    | tar -xz --strip-components=1 -C /usr/local/bin docker/docker

# compose plugin (agent restarts the app with `docker compose ...` after a fix)
RUN mkdir -p /usr/local/lib/docker/cli-plugins \
    && curl -fsSL -o /usr/local/lib/docker/cli-plugins/docker-compose \
         https://github.com/docker/compose/releases/download/v2.29.7/docker-compose-linux-x86_64 \
    && chmod +x /usr/local/lib/docker/cli-plugins/docker-compose

# headless coding assistant chosen for this homework
RUN npm install -g @github/copilot

WORKDIR /opt/responder
COPY requirements.txt ./
RUN pip3 install --break-system-packages --no-cache-dir -r requirements.txt
COPY responder.py collect-evidence.sh responder-task.md autonomy-policy.yaml response.schema.json ./
COPY runbooks/ ./runbooks/
RUN chmod +x collect-evidence.sh runbooks/*.sh

EXPOSE 8001
CMD ["python3", "-m", "uvicorn", "responder:app", "--host", "0.0.0.0", "--port", "8001"]
