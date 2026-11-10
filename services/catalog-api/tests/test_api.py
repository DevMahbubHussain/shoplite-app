import time
from unittest.mock import patch
import pytest
from httpx import AsyncClient

from app.models.order import OrderStatus


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
    assert "id" in order


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
    response = await async_client.get("/metrics")
    assert response.status_code == 200
    text_content = response.text
    assert "http_requests_total" in text_content
    assert "order_queue_depth" in text_content


@pytest.mark.asyncio
async def test_api_prefix_routing(async_client: AsyncClient):
    response = await async_client.get("/api/products")
    assert response.status_code == 200
    assert len(response.json()) >= 2


@pytest.mark.asyncio
async def test_chaos_latency_flag(async_client: AsyncClient):
    with patch.dict("os.environ", {"CHAOS_LATENCY_MS": "50"}):
        start = time.perf_counter()
        response = await async_client.get("/products")
        duration = time.perf_counter() - start
        assert response.status_code == 200
        assert duration >= 0.04


@pytest.mark.asyncio
async def test_chaos_error_rate_flag(async_client: AsyncClient):
    with patch.dict("os.environ", {"CHAOS_ERROR_RATE": "1.0"}):
        response = await async_client.get("/products")
        assert response.status_code == 500
        assert "Chaos fault injected" in response.json()["error"]
