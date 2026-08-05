"""API v1 router aggregation."""
from fastapi import APIRouter

from app.api.v1 import approval
from app.api.v1.endpoints import (
    accreditation_masters,
    admin,
    admin_auditors,
    admin_cb,
    admin_companies,
    archive,
    assignments,
    auditor_memberships,
    auditors,
    auth,
    audit_request,
    cb_auditors,
    cb_entities,
    cb_profile,
    cb_qualifications,
    cert_contracts,
    certification_applications,
    client,
    companies,
    contracts,
    enterprise_audit_applications,
    enterprise_portal,
    esg_master_kpis,
    mappings,
    md_reviews,
    ncr,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(companies.router)
api_router.include_router(admin_companies.router)
api_router.include_router(admin_auditors.router)
api_router.include_router(admin_cb.router)
api_router.include_router(certification_applications.router)
api_router.include_router(client.router)
api_router.include_router(audit_request.router)
api_router.include_router(enterprise_portal.router)
api_router.include_router(enterprise_audit_applications.router)
api_router.include_router(esg_master_kpis.user_router)
api_router.include_router(esg_master_kpis.admin_router)
api_router.include_router(archive.router)
api_router.include_router(ncr.router)
api_router.include_router(approval.router)
api_router.include_router(mappings.router)
api_router.include_router(md_reviews.router)
api_router.include_router(contracts.router)
api_router.include_router(assignments.router)
api_router.include_router(auditors.router)
api_router.include_router(auditor_memberships.router)
api_router.include_router(cb_auditors.router)
api_router.include_router(accreditation_masters.router)
api_router.include_router(cb_profile.router)
api_router.include_router(cb_entities.router)
api_router.include_router(cb_qualifications.router)
api_router.include_router(cert_contracts.router)
api_router.include_router(admin.router)

