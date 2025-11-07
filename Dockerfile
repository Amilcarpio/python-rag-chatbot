FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
COPY README.md .
RUN pip install --no-cache-dir -e .

COPY . .

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["sh", "-c", "\
    echo '=== Waiting for database ===' && \
    until pg_isready -h postgres -U raguser; do sleep 1; done && \
    echo '=== Creating database tables ===' && \
    python3 -c 'from database.connection import Base, engine; Base.metadata.create_all(bind=engine); print(\"✓ Tables created\")' && \
    echo '=== Setting up pgvector ===' && \
    python3 database/setup_pgvector.py && \
    echo '=== Starting API server ===' && \
    uvicorn main:app --host 0.0.0.0 --port 8000"]
