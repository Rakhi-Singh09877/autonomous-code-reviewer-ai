from fastapi import FastAPI
from app.core.config import settings
from app.infrastructure.api.v1.router import api_router

app = FastAPI(
    title=settings.APP_NAME,
    description="Clean Architecture API exposing automated code review, analysis tracking, RAG contexts, and health metrics.",
    version="1.0.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Register the aggregated APIRouter with default API prefix (/api/v1)
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/", tags=["status"])
async def root():
    return {
        "app_name": settings.APP_NAME,
        "environment": settings.APP_ENV,
        "status": "online"
    }
