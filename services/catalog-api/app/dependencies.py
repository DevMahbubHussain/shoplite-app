from collections.abc import AsyncGenerator
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.repositories.order_repository import (
    OrderRepositoryProtocol,
    PostgresOrderRepository,
)
from app.repositories.product_repository import (
    PostgresProductRepository,
    ProductRepositoryProtocol,
)
from app.services.catalog_service import CatalogService
from app.services.order_service import OrderService
from app.services.queue_service import QueueProducerProtocol, RedisQueueService

_redis_queue_instance: RedisQueueService | None = None


def get_queue_service() -> QueueProducerProtocol:
    global _redis_queue_instance
    if _redis_queue_instance is None:
        _redis_queue_instance = RedisQueueService()
    return _redis_queue_instance


def get_product_repository(
    session: AsyncSession = Depends(get_db_session),
) -> ProductRepositoryProtocol:
    return PostgresProductRepository(session)


def get_order_repository(
    session: AsyncSession = Depends(get_db_session),
) -> OrderRepositoryProtocol:
    return PostgresOrderRepository(session)


def get_catalog_service(
    repo: ProductRepositoryProtocol = Depends(get_product_repository),
) -> CatalogService:
    return CatalogService(repo)


def get_order_service(
    order_repo: OrderRepositoryProtocol = Depends(get_order_repository),
    product_repo: ProductRepositoryProtocol = Depends(get_product_repository),
    queue_service: QueueProducerProtocol = Depends(get_queue_service),
) -> OrderService:
    return OrderService(order_repo, product_repo, queue_service)
