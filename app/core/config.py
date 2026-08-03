"""Application configuration."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "ComplAIs API"
    debug: bool = False
    database_url: str = "mysql+pymysql://root:password@localhost:3306/complais?charset=utf8mb4"


settings = Settings()
