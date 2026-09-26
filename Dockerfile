# syntax=docker/dockerfile:1
# Greek Tutor — one image, two targets:
#   runtime (default)  the web app; also runs scripts/migrate.py as the `migrate` service.
#                      --build-arg WITH_CLAUDE_CLI=true adds Claude Code for LLM_BACKEND=claude_cli
#   dev                runtime + dev deps + tests; used by the `test` compose profile

FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app
RUN useradd --create-home --uid 10001 tutor
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY app ./app
COPY templates ./templates
COPY migrations ./migrations
COPY seed ./seed
COPY scripts ./scripts

FROM base AS dev
ENV RUFF_CACHE_DIR=/tmp/ruff-cache
COPY requirements-dev.txt pyproject.toml ./
RUN pip install -r requirements-dev.txt
COPY tests ./tests
USER tutor
CMD ["sh", "-c", "ruff check app tests scripts && pytest -p no:cacheprovider"]

FROM base AS runtime
# Optional: the claude binary for LLM_BACKEND=claude_cli (your own Claude subscription).
# docker compose passes these from .env; the default image stays API-key only.
ARG WITH_CLAUDE_CLI=false
ARG CLAUDE_CLI_VERSION=stable
RUN if [ "$WITH_CLAUDE_CLI" = "true" ]; then \
      apt-get update \
      && apt-get install -y --no-install-recommends curl ca-certificates \
      && rm -rf /var/lib/apt/lists/* \
      && su tutor -c "curl -fsSL https://claude.ai/install.sh | bash -s $CLAUDE_CLI_VERSION" \
      && su tutor -c "/home/tutor/.local/bin/claude --version"; \
    fi
ENV PATH="/home/tutor/.local/bin:${PATH}" \
    DISABLE_AUTOUPDATER=1
USER tutor
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import sys,urllib.request; sys.exit(urllib.request.urlopen('http://127.0.0.1:8080/healthz', timeout=4).status != 200)"
# --proxy-headers: the app sits behind Caddy / a Cloudflare Tunnel, never directly on the internet.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", \
     "--proxy-headers", "--forwarded-allow-ips", "*"]
