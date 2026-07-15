# Local Deployment Guide - Autonomous Code Reviewer

This guide details steps to build, run, and manage the Autonomous Code Reviewer API and database containers locally for development and testing.

---

## Prerequisites
Ensure the following packages are installed on your workstation:
1. **Docker Desktop** (or Docker Engine with Docker Compose v2.0+).
2. **Git** (for local cloning workflows).
3. **Python 3.10+** (only if running the test suite outside of Docker).

---

## Environment Setup
1. Duplicate the sample configuration file from the repository root:
   ```bash
   copy .env.example .env
   ```
2. Open `.env` and fill in the API keys:
   - `ANTHROPIC_API_KEY`: Required for file code review analyses.
   - `OPENAI_API_KEY`: Required for text embedding creation.

---

## Docker Compose Startup
To build images and spin up the multi-container environment:
```bash
docker compose up -d
```
The services running in background daemon mode are:
- `reviewer_backend`: FastAPI app running on port `8000`.
- `reviewer_chromadb`: Standalone vector database server running on port `8001`.

---

## Stopping Containers
To gracefully stop and remove active container processes without erasing volumes:
```bash
docker compose down
```

To stop containers and delete persisted volume databases (ChromaDB index and database tables):
```bash
docker compose down -v
```

---

## Rebuilding Containers
Whenever dependencies in `requirements.txt` or Docker configurations change, force a clean rebuild:
```bash
docker compose up -d --build
```

---

## Accessing Swagger / OpenAPI Documentation
Once containers are running:
- **Interactive Documentation (Swagger UI)**: Navigate to [http://localhost:8000/docs](http://localhost:8000/docs).
- **Alternative Documentation (ReDoc)**: Navigate to [http://localhost:8000/redoc](http://localhost:8000/redoc).
- **Raw OpenAPI Specification JSON**: Navigate to [http://localhost:8000/api/v1/openapi.json](http://localhost:8000/api/v1/openapi.json).

---

## Common Troubleshooting

### 1. Database migrations or "column not found" errors
If columns like `total_files` are missing from local storage, a stale DB schema exists. Purge the SQLite file:
- **Docker**: `docker compose down -v` to delete the volume.
- **Local**: Delete `code_reviewer.db` at the root directory and restart uvicorn.

### 2. Port conflict on port 8000 or 8001
If port `8000` is already in use by another local process, adjust the host port mapping in `docker-compose.yml`:
```yaml
ports:
  - "8080:8000"  # Changes host access to http://localhost:8080
```

### 3. API Keys missing errors
If background reviews log `LLMInvalidAPIKeyException`, check that `ANTHROPIC_API_KEY` is correctly defined in the `.env` file at the root.
