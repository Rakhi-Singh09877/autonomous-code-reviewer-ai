# Production Dockerfile for Autonomous Code Reviewer Backend
FROM python:3.14-slim

# Set environment variables to prevent python from writing pyc and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# Install system dependencies (git for loader, build-essential for treesitter compilation)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Add a secure non-root user and initialize temporary workspace storage
RUN useradd -u 10001 -m appuser && \
    mkdir -p /app/storage/temp && \
    chown -R appuser:appuser /app

# Copy dependency specifications and install first to enable layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend codebase and set ownership permissions
COPY --chown=appuser:appuser . .

# Switch execution context to the secure non-root user
USER appuser

# Expose FastAPI API service port
EXPOSE 8000

# Start the application using uvicorn server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
