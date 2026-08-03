"""Application configuration."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    PROJECT_NAME: str = "ComplAIs API"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = False
    DATABASE_URL: str = "mysql+pymysql://root:password@localhost:3306/complais?charset=utf8mb4"

    @property
    def database_url(self) -> str:
        return self.DATABASE_URL


settings = Settings()
