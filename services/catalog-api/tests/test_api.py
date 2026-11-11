import time
from unittest.mock import patch
import pytest
from httpx import AsyncClient

from app.dependencies import get_order_service, get_queue_service
from app.main import app
from app.models.order import OrderStatus
from app.services.order_service import OrderService


class StaticQueueService:
    def __init__(self, healthy: bool = True, fail_push: bool = False) -> None:
        self.healthy = healthy
        self.fail_push = fail_push

    async def push_order(self, order_id: int, product_id: int, quantity: int) -> None:
        if self.fail_push:
            raise RuntimeError("redis connection lost")

    async def get_queue_depth(self) -> int:
        return 0

    async def check_health(self) -> bool:
        return self.healthy


@pytest.mark.asyncio
async def test_healthz_endpoint(async_client: AsyncClient):
    response = await async_client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_readyz_healthy(async_client: AsyncClient):
    with patch("app.routers.probes.check_database_connection", return_value=True):
        response = await async_client.get("/readyz")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert data["database"] == "connected"
        assert data["redis"] == "connected"


@pytest.mark.asyncio
async def test_readyz_unhealthy_database(async_client: AsyncClient):
    with patch("app.routers.probes.check_database_connection", return_value=False):
        response = await async_client.get("/readyz")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unavailable"
        assert data["database"] == "unreachable"


@pytest.mark.asyncio
async def test_readyz_unhealthy_redis(async_client: AsyncClient):
    with patch("app.routers.probes.check_database_connection", return_value=True):
        app.dependency_overrides[get_queue_service] = lambda: StaticQueueService(healthy=False)
        response = await async_client.get("/readyz")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unavailable"
        assert data["redis"] == "unreachable"


@pytest.mark.asyncio
async def test_list_products(async_client: AsyncClient):
    response = await async_client.get("/products")
    assert response.status_code == 200
    products = response.json()
    assert isinstance(products, list)
    assert len(products) >= 2
    assert products[0]["id"] == 1
    assert "name" in products[0]
    assert "price" in products[0]


@pytest.mark.asyncio
async def test_get_product_by_id_found(async_client: AsyncClient):
    response = await async_client.get("/products/1")
    assert response.status_code == 200
    product = response.json()
    assert product["id"] == 1
    assert product["name"] == "Ultra-Slim Laptop Pro"


@pytest.mark.asyncio
async def test_get_product_by_id_not_found(async_client: AsyncClient):
    response = await async_client.get("/products/9999")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_create_order_success(async_client: AsyncClient):
    order_payload = {"product_id": 1, "quantity": 2}
    response = await async_client.post("/orders", json=order_payload)
    assert response.status_code == 201
    order = response.json()
    assert order["product_id"] == 1
    assert order["quantity"] == 2
    assert order["status"] == OrderStatus.PENDING.value
    assert order["order_id"] == order["id"]
    assert order["completed_at"] is None


@pytest.mark.asyncio
async def test_create_order_queue_failure_returns_503_and_marks_failed(
    async_client: AsyncClient,
    mock_order_repo,
    mock_product_repo,
):
    failing_service = OrderService(
        mock_order_repo,
        mock_product_repo,
        StaticQueueService(fail_push=True),
    )
    app.dependency_overrides[get_order_service] = lambda: failing_service

    response = await async_client.post("/orders", json={"product_id": 1, "quantity": 1})

    assert response.status_code == 503
    persisted_order = mock_order_repo.orders[2]
    assert persisted_order.status == OrderStatus.FAILED.value


@pytest.mark.asyncio
async def test_create_order_invalid_product(async_client: AsyncClient):
    order_payload = {"product_id": 9999, "quantity": 1}
    response = await async_client.post("/orders", json=order_payload)
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_create_order_invalid_quantity(async_client: AsyncClient):
    order_payload = {"product_id": 1, "quantity": 0}
    response = await async_client.post("/orders", json=order_payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_order_by_id_found(async_client: AsyncClient):
    response = await async_client.get("/orders/1")
    assert response.status_code == 200
    order = response.json()
    assert order["id"] == 1
    assert order["status"] == OrderStatus.PENDING.value


@pytest.mark.asyncio
async def test_get_order_by_id_not_found(async_client: AsyncClient):
    response = await async_client.get("/orders/9999")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_metrics_endpoint(async_client: AsyncClient):
    await async_client.get("/products")
    response = await async_client.get("/metrics")
    assert response.status_code == 200
    text_content = response.text
    assert "http_requests_total" in text_content
    assert 'route="/products"' in text_content
    assert "orders_created_total" in text_content
    assert "order_queue_depth" in text_content


@pytest.mark.asyncio
async def test_api_prefix_routing(async_client: AsyncClient):
    response = await async_client.get("/api/products")
    assert response.status_code == 200
    assert len(response.json()) >= 2


@pytest.mark.asyncio
async def test_chaos_latency_flag(async_client: AsyncClient):
    with patch("app.middleware.chaos.settings.CHAOS_LATENCY_MS", 50):
        start = time.perf_counter()
        response = await async_client.get("/products")
        duration = time.perf_counter() - start
        assert response.status_code == 200
        assert duration >= 0.04


@pytest.mark.asyncio
async def test_chaos_error_rate_flag(async_client: AsyncClient):
    with patch("app.middleware.chaos.settings.CHAOS_ERROR_RATE", 1.0):
        response = await async_client.get("/products")
        assert response.status_code == 500
        assert "Chaos fault injected" in response.json()["error"]
