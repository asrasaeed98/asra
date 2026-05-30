FROM python:3.12-slim-bookworm

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc g++ libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY apps/api/pyproject.toml apps/api/README.md /app/
COPY apps/api/src /app/src

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir .

ENV SESSION_DATA_DIR=/tmp/session_data

CMD ["sh", "-c", "uvicorn findings_api.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
