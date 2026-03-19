FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && pip check

COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini .
COPY scripts/migrate_and_start.sh ./migrate_and_start.sh
RUN chmod +x ./migrate_and_start.sh

EXPOSE 8000

ENTRYPOINT ["./migrate_and_start.sh"]

ARG PRODUCTION=false
CMD ["sh", "-c", "if [ \"$PRODUCTION\" = \"true\" ]; then uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2; else uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload; fi"]
