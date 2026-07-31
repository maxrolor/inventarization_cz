from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    # База данных
    db_host: str = Field(..., env="DB_HOST")
    db_port: int = Field(..., env="DB_PORT")
    db_user: str = Field(..., env="DB_USER")
    db_password: str = Field(..., env="DB_PASSWORD")
    db_name: str = Field(..., env="DB_NAME")

    # JWT
    secret_key: str = Field(..., env="SECRET_KEY")
    algorithm: str = Field(..., env="ALGORITHM")
    access_token_expire_minutes: int = Field(..., env="ACCESS_TOKEN_EXPIRE_MINUTES")

    # SMTP
    smtp_host: str = Field(..., env="SMTP_HOST")
    smtp_port: int = Field(..., env="SMTP_PORT")
    smtp_user: str = Field(..., env="SMTP_USER")
    smtp_password: str = Field(..., env="SMTP_PASSWORD")
    smtp_from: str = Field(..., env="SMTP_FROM")

    # Dadata
    dadata_api_key: str = Field("", env="DADATA_API_KEY")

    # Celery (опционально, чтобы избежать ошибок extra_forbidden)
    celery_broker_url: Optional[str] = None
    celery_result_backend: Optional[str] = None

    # Шифрование токена
    fernet_key: str = Field(..., env="FERNET_KEY")

    # Честный знак
    cz_api_base_url: str = Field(
        "https://markirovka.sandbox.crptech.ru/api/v3/true-api",
        env="CZ_API_BASE_URL"
    )
    cz_api_timeout: int = Field(60, env="CZ_API_TIMEOUT")
    cz_api_max_retries: int = Field(3, env="CZ_API_MAX_RETRIES")

    @property
    def database_url(self) -> str:
        return f"postgresql+asyncpg://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"  # разрешаем любые дополнительные поля в .env

settings = Settings()