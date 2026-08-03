"""ComplAIs FastAPI application entry point."""
from fastapi import FastAPI

from app.core.config import settings

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="ComplAIs certification management platform API",
)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
