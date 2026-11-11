from pydantic_settings import BaseSettings, SettingsConfigDict


class WorkerSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    SERVICE_NAME: str = "order-worker"
    LOG_LEVEL: str = "INFO"

    DATABASE_URL: str = "postgresql+asyncpg://shoplite_user:shoplite_password@postgres:5432/shoplite_db"
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PENDING_QUEUE: str = "orders:pending"
    REDIS_PROCESSING_QUEUE: str = "orders:processing"
    REDIS_POP_TIMEOUT: int = 2

    METRICS_PORT: int = 9102

    OTEL_EXPORTER_OTLP_ENDPOINT: str = "http://tempo:4318/v1/traces"
    OTEL_ENABLED: bool = False

    PROCESSING_DELAY_MIN_SECONDS: float = 1.0
    PROCESSING_DELAY_MAX_SECONDS: float = 2.0
    RETRY_DELAY_SECONDS: float = 1.0

    CHAOS_SLOW_DB: bool = False
    CHAOS_MEMORY_LEAK: bool = False


worker_settings = WorkerSettings()
