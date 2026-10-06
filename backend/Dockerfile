# syntax=docker/dockerfile:1.7

# ---- Stage 1: Build ----
FROM python:3.11-slim AS builder

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DEFAULT_TIMEOUT=120 \
    PIP_RETRIES=10

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir --default-timeout=120 --retries=10 -r requirements.txt

# ---- Stage 2: Production ----
FROM python:3.11-slim

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Security: run as non-root user
RUN useradd -m appuser

# Copy application code
COPY . .

# Create data directory with correct ownership
RUN mkdir -p /app/data /app/logs && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen('http://localhost:' + os.getenv('PORT', '8000') + '/health')" || exit 1

CMD ["sh", "-c", "exec uvicorn src.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
