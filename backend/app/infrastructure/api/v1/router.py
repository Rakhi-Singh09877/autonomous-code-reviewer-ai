from fastapi import APIRouter
from app.infrastructure.api.v1.endpoints import upload, status, reports

api_router = APIRouter()

# Register all sub-routers with logical tagging
api_router.include_router(upload.router, tags=["analysis"])
api_router.include_router(status.router, tags=["analysis"])
api_router.include_router(reports.router, tags=["reports"])
