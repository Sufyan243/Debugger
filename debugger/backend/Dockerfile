FROM python:3.11-slim

WORKDIR /app

# util-linux provides flock(1) used by migrate_and_start.sh to serialise
# concurrent migration runs when the container starts with multiple workers.
RUN apt-get update && apt-get install -y --no-install-recommends util-linux \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements-dev.txt ./
ARG INSTALL_DEV=false
RUN if [ "$INSTALL_DEV" = "true" ]; then \
      pip install --no-cache-dir -r requirements-dev.txt && pip check; \
    else \
      pip install --no-cache-dir -r requirements.txt && pip check; \
    fi

COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini .
COPY scripts/migrate_and_start.sh ./migrate_and_start.sh
COPY seccomp/ ./seccomp/
RUN chmod +x ./migrate_and_start.sh

# Run as non-root — never run application code as root in production.
RUN adduser --disabled-password --gecos "" appuser
USER appuser

EXPOSE 8000

ENTRYPOINT ["./migrate_and_start.sh"]

ARG PRODUCTION=false
CMD ["sh", "-c", "if [ \"$PRODUCTION\" = \"true\" ]; then uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2; else uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload; fi"]
