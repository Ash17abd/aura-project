# Production Dockerfile for AURA 3D Learning Lab
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8501 \
    ENVIRONMENT=production

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files (secrets excluded via .dockerignore)
COPY . .

# Expose production port
EXPOSE 8501

# Production Healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl --fail http://127.0.0.1:${PORT:-8501}/api/health || exit 1

# Start production FastAPI server using dynamic $PORT
CMD ["sh", "-c", "uvicorn web_server:app --host 0.0.0.0 --port ${PORT:-8501}"]
