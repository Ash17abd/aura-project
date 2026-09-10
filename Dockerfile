# Production Dockerfile for AURA 3D Learning Lab
# Universal support for Hugging Face Spaces, Koyeb, Railway, and standard Docker
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=7860 \
    ENVIRONMENT=production

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set up user for Hugging Face Spaces & cloud security compliance
RUN useradd -m -u 1000 user
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files (secrets excluded via .dockerignore)
COPY --chown=user:user . .

# Ensure directory permissions for runtime state & memory
RUN chown -R user:user /app
USER user

# Expose production ports (7860 for Hugging Face Spaces, 8501 for local/cloud)
EXPOSE 7860 8501

# Production Healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl --fail http://127.0.0.1:${PORT:-7860}/api/health || exit 1

# Start production FastAPI server using dynamic $PORT
CMD ["sh", "-c", "uvicorn web_server:app --host 0.0.0.0 --port ${PORT:-7860}"]
