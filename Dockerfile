# Base stage
FROM python:3.11-slim AS base

WORKDIR /app

# Install system dependencies (ARM64 compatible)
# Note: opencv-python-headless still requires libxcb1 for some internal operations
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    ffmpeg \
    libglib2.0-0 \
    libgomp1 \
    libxcb1 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better layer caching
COPY backend/pyproject.toml ./backend/

# Development stage
FROM base AS development
# Copy backend code
COPY backend/ ./backend/
WORKDIR /app/backend

# Install dependencies (API extras only - no ML stack)
RUN pip install --no-cache-dir -e ".[api]" && \
    pip install --no-cache-dir pytest ruff

# Create required directories
RUN mkdir -p data/videos/raw data/videos/processed data/analysis_cache data/database

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# Production stage
FROM base AS production
# Copy backend code
COPY backend/ ./backend/
WORKDIR /app/backend

# Install dependencies (API extras only - no ML stack)
RUN pip install --no-cache-dir -e ".[api]"

# Create required directories
RUN mkdir -p data/videos/raw data/videos/processed data/analysis_cache data/database

# Create non-root user
RUN adduser --disabled-password --gecos '' appuser && \
    chown -R appuser:appuser /app
USER appuser

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
