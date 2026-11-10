from datetime import datetime, timezone
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.dependencies import (
    get_catalog_service,
    get_order_repository,
    get_order_service,
    get_product_repository,
    get_queue_service,
)
from app.main import app
from app.models.order import Order, OrderStatus
from app.models.product import Product
from app.services.catalog_service import CatalogService
from app.services.order_service import OrderService


class MockProductRepository:
    def __init__(self) -> None:
        self.products: dict[int, Product] = {
            1: Product(
                id=1,
                name="Ultra-Slim Laptop Pro",
                description="High performance developer laptop",
                price=1499.99,
                stock=50,
                created_at=datetime.now(timezone.utc),
            ),
            2: Product(
                id=2,
                name="Mechanical Keyboard",
                description="Hot-swappable tactile switches",
                price=129.50,
                stock=100,
                created_at=datetime.now(timezone.utc),
            ),
        }

    async def get_all(self) -> list[Product]:
        return list(self.products.values())

    async def get_by_id(self, product_id: int) -> Product | None:
        return self.products.get(product_id)

    async def count(self) -> int:
        return len(self.products)

    async def create(self, product: Product) -> Product:
        new_id = max(self.products.keys(), default=0) + 1
        product.id = new_id
        self.products[new_id] = product
        return product

    async def bulk_create(self, products: list[Product]) -> None:
        for p in products:
            await self.create(p)


class MockOrderRepository:
    def __init__(self) -> None:
        self.orders: dict[int, Order] = {
            1: Order(
                id=1,
                product_id=1,
                quantity=1,
                status=OrderStatus.PENDING.value,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
        }

    async def create(self, order: Order) -> Order:
        new_id = max(self.orders.keys(), default=0) + 1
        order.id = new_id
        now = datetime.now(timezone.utc)
        if getattr(order, "created_at", None) is None:
            order.created_at = now
        if getattr(order, "updated_at", None) is None:
            order.updated_at = now
        self.orders[new_id] = order
        return order

    async def get_by_id(self, order_id: int) -> Order | None:
        return self.orders.get(order_id)

    async def update_status(self, order_id: int, status: str) -> Order | None:
        order = self.orders.get(order_id)
        if order:
            order.status = status
        return order


class MockQueueService:
    def __init__(self, healthy: bool = True) -> None:
        self.messages: list[dict] = []
        self.healthy = healthy

    async def push_order(self, order_id: int, product_id: int, quantity: int) -> None:
        self.messages.append({"order_id": order_id, "product_id": product_id, "quantity": quantity})

    async def get_queue_depth(self) -> int:
        return len(self.messages)

    async def check_health(self) -> bool:
        return self.healthy


@pytest.fixture
def mock_product_repo() -> MockProductRepository:
    return MockProductRepository()


@pytest.fixture
def mock_order_repo() -> MockOrderRepository:
    return MockOrderRepository()


@pytest.fixture
def mock_queue_service() -> MockQueueService:
    return MockQueueService()


@pytest_asyncio.fixture
async def async_client(
    mock_product_repo: MockProductRepository,
    mock_order_repo: MockOrderRepository,
    mock_queue_service: MockQueueService,
) -> AsyncClient:
    catalog_service = CatalogService(mock_product_repo)
    order_service = OrderService(mock_order_repo, mock_product_repo, mock_queue_service)

    app.dependency_overrides[get_product_repository] = lambda: mock_product_repo
    app.dependency_overrides[get_order_repository] = lambda: mock_order_repo
    app.dependency_overrides[get_queue_service] = lambda: mock_queue_service
    app.dependency_overrides[get_catalog_service] = lambda: catalog_service
    app.dependency_overrides[get_order_service] = lambda: order_service

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client

    app.dependency_overrides.clear()
