from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
