from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import async_session_factory, engine
from app.middleware.chaos import ChaosMiddleware
from app.middleware.metrics_middleware import MetricsMiddleware
from app.models.base import Base
from app.observability.logging import logger
from app.observability.tracing import init_tracer
from app.repositories.product_repository import PostgresProductRepository
from app.routers.orders import router as orders_router
from app.routers.products import router as products_router
from app.routers.probes import router as probes_router
from app.services.catalog_service import CatalogService


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.SERVICE_NAME} in {settings.ENVIRONMENT} mode")

    if settings.OTEL_ENABLED:
        init_tracer(
            service_name=settings.SERVICE_NAME,
            endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT,
            enabled=True,
        )

    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with async_session_factory() as session:
            repo = PostgresProductRepository(session)
            service = CatalogService(repo)
            seeded = await service.seed_initial_products_if_empty()
            if seeded > 0:
                logger.info(f"Database initialized with {seeded} seed products")
    except Exception as exc:
        logger.warning(f"Database initialization deferred (database not ready yet): {exc}")

    yield

    logger.info(f"Shutting down {settings.SERVICE_NAME}")
    await engine.dispose()


app = FastAPI(
    title="ShopLite Catalog API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(MetricsMiddleware)
app.add_middleware(ChaosMiddleware)

# Root level endpoints
app.include_router(probes_router)
app.include_router(products_router)
app.include_router(orders_router)

# Also mount under /api for reverse proxy compatibility
app.include_router(probes_router, prefix="/api")
app.include_router(products_router, prefix="/api")
app.include_router(orders_router, prefix="/api")
