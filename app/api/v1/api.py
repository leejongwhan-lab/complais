"""API v1 router aggregation."""
from fastapi import APIRouter

from app.api.v1.endpoints import certification_applications, companies

api_router = APIRouter()
api_router.include_router(companies.router)
api_router.include_router(certification_applications.router)
