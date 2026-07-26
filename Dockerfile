FROM node:24-alpine AS frontend

WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend ./
RUN npm run build:embed

FROM python:3.11-slim

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
COPY data ./data
COPY results ./results
COPY --from=frontend /src/ai_takehome/rag/static ./src/ai_takehome/rag/static
RUN pip install --no-cache-dir .

ENV GROUNDED_OPS_HOME=/app \
    PYTHONPATH=/app/src \
    PORT=8000
EXPOSE 8000
CMD ["sh", "-c", "rag ingest data/corpus && exec uvicorn ai_takehome.rag.api:app --host 0.0.0.0 --port ${PORT:-8000}"]
