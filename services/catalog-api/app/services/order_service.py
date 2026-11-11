from fastapi import HTTPException, status

from app.models.order import Order, OrderStatus
from app.observability.logging import logger
from app.observability.metrics import ORDERS_CREATED_TOTAL
from app.repositories.order_repository import OrderRepositoryProtocol
from app.repositories.product_repository import ProductRepositoryProtocol
from app.schemas.order import OrderCreate, OrderOut
from app.services.queue_service import QueueProducerProtocol


class OrderService:
    def __init__(
        self,
        order_repo: OrderRepositoryProtocol,
        product_repo: ProductRepositoryProtocol,
        queue_service: QueueProducerProtocol,
    ) -> None:
        self.order_repo = order_repo
        self.product_repo = product_repo
        self.queue_service = queue_service

    async def create_order(self, dto: OrderCreate) -> OrderOut:
        product = await self.product_repo.get_by_id(dto.product_id)
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product with id {dto.product_id} not found",
            )

        new_order = Order(
            product_id=dto.product_id,
            quantity=dto.quantity,
            status=OrderStatus.PENDING.value,
        )
        saved_order = await self.order_repo.create(new_order)

        try:
            await self.queue_service.push_order(
                order_id=saved_order.id,
                product_id=saved_order.product_id,
                quantity=saved_order.quantity,
            )
        except Exception as exc:
            # Persisted order must not linger as PENDING when enqueue failed
            await self.order_repo.update_status(saved_order.id, OrderStatus.FAILED.value)
            logger.error(
                f"Failed to enqueue order {saved_order.id}; marked FAILED",
                extra={"order_id": saved_order.id},
                exc_info=exc,
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Order could not be enqueued; please retry",
            ) from exc

        ORDERS_CREATED_TOTAL.inc()

        logger.info(
            "Order created successfully",
            extra={"order_id": saved_order.id, "product_id": saved_order.product_id},
        )

        return OrderOut.model_validate(saved_order)

    async def get_order_by_id(self, order_id: int) -> OrderOut | None:
        order = await self.order_repo.get_by_id(order_id)
        if not order:
            return None
        return OrderOut.model_validate(order)
