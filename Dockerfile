FROM python:3.11-slim AS builder

WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends     gcc libpq-dev && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY app/ ./app/
COPY pipeline/ ./pipeline/
COPY dashboard/ ./dashboard/
COPY scripts/ ./scripts/
RUN pip install --no-cache-dir --upgrade pip &&     pip install --no-cache-dir ".[dev]"

FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends     libgl1 libglib2.0-0 libsm6 libxext6 libxrender-dev libgomp1     && rm -rf /var/lib/apt/lists/*

COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY app/ ./app/
COPY pipeline/ ./pipeline/
COPY dashboard/ ./dashboard/
COPY scripts/ ./scripts/
COPY docs/ ./docs/
COPY tests/ ./tests/
COPY README.md ./

ENV PYTHONPATH=/app
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
