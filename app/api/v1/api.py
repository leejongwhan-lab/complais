"""API v1 router aggregation."""
from fastapi import APIRouter

from app.api.v1 import approval
from app.api.v1.endpoints import (
    admin,
    assignments,
    auditors,
    auth,
    cb_entities,
    cert_contracts,
    certification_applications,
    companies,
    contracts,
    mappings,
    md_reviews,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(companies.router)
api_router.include_router(certification_applications.router)
api_router.include_router(approval.router)
api_router.include_router(mappings.router)
api_router.include_router(md_reviews.router)
api_router.include_router(contracts.router)
api_router.include_router(assignments.router)
api_router.include_router(auditors.router)
api_router.include_router(cb_entities.router)
api_router.include_router(cert_contracts.router)
api_router.include_router(admin.router)

