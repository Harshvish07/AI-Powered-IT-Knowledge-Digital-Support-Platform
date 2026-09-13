# Multi-stage: a shared `base` layer, then `dev` (used by the root
# docker-compose.yml for local development — hot reload, dev/test tooling
# included) and `production` (lean, prod dependencies only, non-root user,
# no reload). See docs/deployment.md for how to build/run the production
# target; docker-compose.yml pins `target: dev` so `docker compose up`
# behavior is unchanged from earlier phases.

FROM python:3.12-slim AS base
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
# psycopg[binary] ships prebuilt wheels, so no compiler/libpq-dev is needed here.
COPY requirements.txt ./


FROM base AS dev
COPY requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements-dev.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]


FROM base AS production
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# Runs as an unprivileged user — the container's filesystem access is
# limited to what this user owns, which is only ever this app's own code
# and upload storage directory, not root-level system paths.
RUN useradd --create-home --uid 1000 appuser \
    && mkdir -p storage/uploads \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/health', timeout=3).status == 200 else 1)"

# Single worker by default: the rate limiter (slowapi) keeps its counters
# in-process, so multiple workers would each enforce limits independently,
# quietly loosening the effective rate limit by a factor of worker count —
# see docs/deployment.md "Performance considerations" before raising this.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
