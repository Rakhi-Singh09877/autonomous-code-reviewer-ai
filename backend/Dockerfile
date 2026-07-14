# Production Dockerfile for Autonomous Code Reviewer Backend
FROM python:3.10-slim

WORKDIR /workspace

# Install system dependencies (git, build-essential for treesitter, sqlite3/postgres libraries)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    build-essential \
    libpq-dev \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Copy and install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend files
COPY . .

# Expose API port and Model Context Protocol (MCP) port
EXPOSE 8000
EXPOSE 8500

# Default command for API container
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
