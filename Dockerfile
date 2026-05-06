# Top-level Dockerfile that Railway / Render / Fly.io / Cloud Run auto-detect.
#
# Builds the Event Intelligence API. Local dev still uses
# infra/docker/docker-compose.dev.yml; that compose file overrides the CMD
# with --reload and mounts the repo as a volume.

FROM python:3.12-slim

# Avoid bytecode cache + line-buffer stdout so logs show up in Railway.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PIP_NO_CACHE_DIR=1

# psycopg2-binary needs libpq + build essentials for some platforms; slim doesn't ship them.
RUN apt-get update \
 && apt-get install -y --no-install-recommends gcc libpq-dev \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install deps first for layer caching.
COPY apps/api/requirements.txt ./apps/api/requirements.txt
RUN pip install -r apps/api/requirements.txt

# Copy the rest of the repo.
COPY . .

# Railway / Render / Fly inject $PORT. Default to 8000 for local docker run.
ENV PORT=8000
EXPOSE 8000

# Use sh -c so $PORT is expanded at runtime.
CMD ["sh", "-c", "python -m uvicorn apps.api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
