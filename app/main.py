import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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


# 정적 목업 페이지(플랫폼 어드민 대시보드 등) 서빙.
# 주의: "/" 마운트는 경로 전체를 prefix로 가로채므로, 위의 API 라우터들보다
# 반드시 나중에 등록해야 한다. 순서가 바뀌면 /api/v1/... 요청까지
# StaticFiles가 먼저 가로채 404를 반환하게 된다.
static_dir = os.path.join(os.path.dirname(__file__), "static")

if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="root")
