# Dockerfile
# What this file does:
# - Builds a clean backend image so "docker compose up" works everywhere.

FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

EXPOSE 8000
# Run via gunicorn + uvicorn workers for production robustness
CMD ["sh", "-c", "gunicorn app.main:app -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000 --workers ${ROPT_WORKERS:-2}"]
