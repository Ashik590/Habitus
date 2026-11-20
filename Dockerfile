FROM node:24-bookworm-slim AS frontend
WORKDIR /build
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
ENV VITE_API_BASE_URL=/api/v1
RUN npm run build

FROM python:3.12-slim-bookworm
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HF_HOME=/app/.cache/huggingface \
    OMP_NUM_THREADS=1 \
    FRONTEND_DIST_DIR=/app/frontend-dist
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
# Download model files during the build instead of the first user request.
RUN python -c "from faster_whisper.utils import download_model; download_model('tiny')"
COPY backend/ ./
COPY --from=frontend /build/dist /app/frontend-dist
RUN useradd --create-home appuser && chown -R appuser:appuser /app
USER appuser
EXPOSE 10000
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-10000} --workers 1"]
