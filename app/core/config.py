"""Application configuration."""
from pydantic_settings import BaseSettings, SettingsConfigDict


def _normalize_database_url(url: str) -> str:
    """Render often injects postgres://; SQLAlchemy expects postgresql://."""
    if url.startswith("postgres://"):
        return "postgresql://" + url[len("postgres://") :]
    return url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    PROJECT_NAME: str = "ComplAIs API"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = False
    DATABASE_URL: str = "mysql+pymysql://root:password@localhost:3306/complais?charset=utf8mb4"
    SECRET_KEY: str = "YOUR_SUPER_SECRET_KEY_CHANGE_THIS"
    UPLOAD_DIR: str = "uploads"

    @property
    def database_url(self) -> str:
        return _normalize_database_url(self.DATABASE_URL)


settings = Settings()
