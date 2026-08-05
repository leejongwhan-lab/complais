import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1.api import api_router
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


@app.get("/health", tags=["health"])
def health_check():
    return {"status": "ok", "project": "ComplAIs API Core"}


# ---- Portal page routes (어드민 / 기업 포털 분리) ----
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


@app.get("/enterprise/dashboard", include_in_schema=False)
@app.get("/enterprise", include_in_schema=False)
def enterprise_dashboard_page():
    """기업 포털 메인 — 사이드 패널 4대 영역."""
    return FileResponse(
        _template_path("enterprise_dashboard.html"),
        media_type="text/html; charset=utf-8",
    )


@app.get("/admin/dashboard", include_in_schema=False)
@app.get("/admin", include_in_schema=False)
def admin_dashboard_page():
    """플랫폼 어드민 진입점."""
    return FileResponse(
        _template_path("admin_dashboard.html"),
        media_type="text/html; charset=utf-8",
    )


# 정적 목업 페이지(플랫폼 어드민 대시보드 등) 서빙.
# 주의: "/" 마운트는 경로 전체를 prefix로 가로채므로, 위의 API/페이지 라우터들보다
# 반드시 나중에 등록해야 한다.
if os.path.exists(_STATIC_DIR):
    app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")
    app.mount("/", StaticFiles(directory=_STATIC_DIR, html=True), name="root")
