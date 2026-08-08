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

    # PortOne identity verification (test/sandbox) — never commit real secrets
    # V1 SDK: IMP.init(PORTONE_IMP_CODE) + IMP.certification
    # V2 SDK: PortOne.requestIdentityVerification({ storeId, channelKey })
    PORTONE_IMP_CODE: str = ""
    PORTONE_STORE_ID: str = ""
    PORTONE_CHANNEL_KEY_KAKAO: str = ""
    PORTONE_CHANNEL_KEY_NAVER: str = ""
    PORTONE_API_SECRET: str = ""
    # true|1|yes → always allow mock identity button; also auto-enabled when keys missing
    PORTONE_ALLOW_MOCK: bool = True

    # 심사원 비밀유지·공평성 서약서 유효기간 (일). POST conduct-sign 시 expires_at 산출에 사용.
    CONDUCT_SIGN_VALIDITY_DAYS: int = 365

    @property
    def database_url(self) -> str:
        return _normalize_database_url(self.DATABASE_URL)

    @property
    def portone_configured(self) -> bool:
        return bool(
            (self.PORTONE_IMP_CODE or "").strip()
            or (
                (self.PORTONE_STORE_ID or "").strip()
                and (
                    (self.PORTONE_CHANNEL_KEY_KAKAO or "").strip()
                    or (self.PORTONE_CHANNEL_KEY_NAVER or "").strip()
                )
            )
        )


settings = Settings()
