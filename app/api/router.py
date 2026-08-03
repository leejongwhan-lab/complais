"""Aggregate API routers."""
from fastapi import APIRouter

from app.api import certification_applications, companies

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(companies.router)
api_router.include_router(certification_applications.router)
