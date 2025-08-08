# Base stage
FROM python:3.11-slim as base

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY backend/pyproject.toml ./

# Development stage
FROM base as development
COPY backend/ ./backend/
RUN pip install --no-cache-dir -e . && \
    pip install --no-cache-dir pytest ruff
RUN mkdir -p data/videos/raw data/videos/processed data/analysis_cache data/database
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# Production stage
FROM base as production
RUN pip install --no-cache-dir -e .
COPY backend/ ./backend/
RUN mkdir -p data/videos/raw data/videos/processed data/analysis_cache data/database
RUN adduser --disabled-password --gecos '' appuser && \
    chown -R appuser:appuser /app
USER appuser
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
