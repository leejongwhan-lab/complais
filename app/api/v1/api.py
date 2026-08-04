"""API v1 router aggregation."""
from fastapi import APIRouter

from app.api.v1 import approval
from app.api.v1.endpoints import certification_applications, companies, mappings

api_router = APIRouter()
api_router.include_router(companies.router)
api_router.include_router(certification_applications.router)
api_router.include_router(approval.router)
api_router.include_router(mappings.router)

