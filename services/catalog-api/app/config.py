from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    SERVICE_NAME: str = "catalog-api"
    ENVIRONMENT: str = "production"
    LOG_LEVEL: str = "INFO"

    DATABASE_URL: str = "postgresql+asyncpg://shoplite_user:shoplite_password@postgres:5432/shoplite_db"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 5
    DB_POOL_TIMEOUT: float = 30.0

    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PENDING_QUEUE: str = "orders:pending"
    REDIS_PROCESSING_QUEUE: str = "orders:processing"

    OTEL_EXPORTER_OTLP_ENDPOINT: str = "http://tempo:4318/v1/traces"
    OTEL_ENABLED: bool = False

    CHAOS_LATENCY_MS: int = 0
    CHAOS_ERROR_RATE: float = 0.0


settings = Settings()
