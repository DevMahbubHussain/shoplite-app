from app.repositories.order_repository import (
    OrderRepositoryProtocol,
    PostgresOrderRepository,
)
from app.repositories.product_repository import (
    PostgresProductRepository,
    ProductRepositoryProtocol,
)

__all__ = [
    "ProductRepositoryProtocol",
    "PostgresProductRepository",
    "OrderRepositoryProtocol",
    "PostgresOrderRepository",
]
