from enum import StrEnum
from functools import lru_cache

from pydantic import PositiveInt, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class LogLevel(StrEnum):
    CRITICAL = "CRITICAL"
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"
    DEBUG = "DEBUG"
    NOTSET = "NOTSET"


class Settings(BaseSettings):
    # - APP -
    app_host: str = "0.0.0.0"  # noqa: S104
    app_port: int = 8000
    app_title: str = "ERP API"
    app_workers: PositiveInt = 1
    worker_thread_pool_size: PositiveInt = 40

    # - Env Control -
    app_env: str = "DEV"

    # - PostgreSQL -
    postgres_host: str = "postgres-erp-api"
    postgres_port: int = 5432
    postgres_user: str = "erp"
    postgres_pass: SecretStr = SecretStr("erp")
    postgres_db: str = "erp"
    postgres_echo: bool = False
    postgres_pool_size: PositiveInt = 5
    postgres_max_overflow: int = 10

    # - Redis -
    redis_host: str = "redis-erp-api"
    redis_port: int = 6379
    redis_pass: SecretStr | None = None
    redis_db: int = 0

    # - Resumo (Q4: fontes simuladas) -
    resumo_timeout: float = 1.0
    resumo_tentativas: PositiveInt = 2
    resumo_latencia_simulada: tuple[float, float] = (0.05, 0.3)
    resumo_backoff_base: float = 0.2
    resumo_backoff_teto: float = 2.0

    # - Estoque -
    estoque_baixo_limite: PositiveInt = 10

    # - Cache -
    cache_ttl_produtos: float = 30

    # - Auth -
    auth_username: str = "lidertecnica"
    auth_password: SecretStr = SecretStr("password123!")
    jwt_secret: SecretStr = SecretStr("change-me")
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: PositiveInt = 60

    # - Metrics -
    metrics_enabled: bool = True

    # - CORS -
    cors_origins: list[str] = ["*"]

    # - Logging (Local) -
    log_level: LogLevel = LogLevel.INFO
    log_dir_path: str = "logs"

    # - Development -
    dev_uvicorn_reload: bool = False

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_comma_separated(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_pass.get_secret_value()}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def redis_url(self) -> str:
        auth = f":{self.redis_pass.get_secret_value()}@" if self.redis_pass else ""
        return f"redis://{auth}{self.redis_host}:{self.redis_port}/{self.redis_db}"


@lru_cache(1)
def get_settings() -> Settings:
    return Settings()
