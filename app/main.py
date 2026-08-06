import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1.api import api_router
from app.api.v1.endpoints import admin_htmx
from app.core.config import settings
from app.routers import auditors  # 심사원 라우터 import

app = FastAPI(
    title="ComplAIs API Core",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 기존 v1 라우터 (companies, approvals 등)
app.include_router(api_router, prefix=settings.API_V1_STR)

# 심사원 라우터 등록
app.include_router(auditors.router, prefix=settings.API_V1_STR)

# Admin HTMX HTML partials (JWT) — /admin/partials/*
app.include_router(admin_htmx.router, prefix="/admin/partials")


@app.get("/health", tags=["health"])
def health_check():
    return {"status": "ok", "project": "ComplAIs API Core"}


# ---- Portal page routes (어드민 / 기업 포털 분리) ----
# 단일 실사용 UI = FastAPI HTML (맥북·아이맥 작업 통일)
_BASE_DIR = os.path.dirname(__file__)
_TEMPLATES_DIR = os.path.join(_BASE_DIR, "templates")
_STATIC_DIR = os.path.join(_BASE_DIR, "static")


def _template_path(*names: str) -> str:
    """templates 우선, 없으면 static 폴백."""
    for name in names:
        path = os.path.join(_TEMPLATES_DIR, name)
        if os.path.exists(path):
            return path
        path = os.path.join(_STATIC_DIR, name)
        if os.path.exists(path):
            return path
    raise FileNotFoundError(f"template not found: {names}")


@app.get("/", include_in_schema=False)
def portal_index_page():
    """통합 포탈 진입점 — 4대 포탈 체계."""
    return FileResponse(
        _template_path("portal_index.html"),
        media_type="text/html; charset=utf-8",
    )


# ── 1. Platform Admin (최상위) ──────────────────────────────────────
@app.get("/admin/dashboard", include_in_schema=False)
@app.get("/admin", include_in_schema=False)
def admin_dashboard_page():
    """플랫폼 전체 어드민 — CB/기업/심사원 통합 관리."""
    return FileResponse(
        _template_path("platform_admin_dashboard.html", "admin_dashboard.html"),
        media_type="text/html; charset=utf-8",
    )


# ── 2. CB Portal ────────────────────────────────────────────────────
@app.get("/cb-portal/dashboard", include_in_schema=False)
@app.get("/cb-admin", include_in_schema=False)  # 하위 호환 별칭
def cb_portal_dashboard_page():
    """CB(인증기관) 포털 대시보드."""
    return FileResponse(
        _template_path("cb_admin_dashboard.html", "cb_portal.html"),
        media_type="text/html; charset=utf-8",
    )


@app.get("/cb-portal/review.html", include_in_schema=False)
def cb_portal_review_page():
    """CB — MD 검토/승인."""
    return FileResponse(
        _template_path("cb_application_review.html", "cb_md_review.html"),
        media_type="text/html; charset=utf-8",
    )


@app.get("/cb-portal/assign.html", include_in_schema=False)
@app.get("/cb-portal/assignments", include_in_schema=False)
def cb_portal_assignments_page():
    """CB — 심사원 배정."""
    return FileResponse(
        _template_path("cb_portal_assignments.html"),
        media_type="text/html; charset=utf-8",
    )


@app.get("/cb-portal/contracts", include_in_schema=False)
def cb_portal_contracts_page():
    """CB — 계약 목록."""
    return FileResponse(
        _template_path("cb_portal_contracts.html"),
        media_type="text/html; charset=utf-8",
    )


@app.get("/cb-portal", include_in_schema=False)
def cb_portal_page():
    """CB 포털 홈."""
    return FileResponse(
        _template_path("cb_portal.html", "cb_admin_dashboard.html"),
        media_type="text/html; charset=utf-8",
    )


# ── 3. Enterprise Portal ────────────────────────────────────────────
@app.get("/enterprise/dashboard", include_in_schema=False)
@app.get("/enterprise", include_in_schema=False)
def enterprise_dashboard_page():
    """기업 포털 메인."""
    return FileResponse(
        _template_path("enterprise_dashboard.html", "client_portal.html"),
        media_type="text/html; charset=utf-8",
    )


@app.get("/client", include_in_schema=False)
@app.get("/client-portal", include_in_schema=False)
def client_portal_page():
    """기업 클라이언트 포탈 (별칭)."""
    return FileResponse(
        _template_path("client_portal.html", "enterprise_dashboard.html"),
        media_type="text/html; charset=utf-8",
    )


@app.get("/apply", include_in_schema=False)
def enterprise_apply_page():
    """기업 MD/인증 신청."""
    return FileResponse(
        _template_path("enterprise_md_apply.html"),
        media_type="text/html; charset=utf-8",
    )


# ── 4. Auditor Portal ───────────────────────────────────────────────
@app.get("/auditor", include_in_schema=False)
@app.get("/auditor-portal", include_in_schema=False)
def auditor_portal_page():
    """인증심사원 포털."""
    return FileResponse(
        _template_path("auditor_portal.html"),
        media_type="text/html; charset=utf-8",
    )


@app.get("/login", include_in_schema=False)
def login_page():
    return FileResponse(
        _template_path("login.html"),
        media_type="text/html; charset=utf-8",
    )


# 정적 자산 (/static/*). 루트 mount("/") 는 라우트와 충돌하므로 제거 — 단일 진입은 "/" 라우트.
if os.path.exists(_STATIC_DIR):
    app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")
