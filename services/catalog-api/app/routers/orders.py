from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import get_order_service
from app.schemas.order import OrderCreate, OrderOut
from app.services.order_service import OrderService

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
async def create_order(
    payload: OrderCreate,
    service: OrderService = Depends(get_order_service),
) -> OrderOut:
    return await service.create_order(payload)


@router.get("/{order_id}", response_model=OrderOut)
async def get_order(
    order_id: int,
    service: OrderService = Depends(get_order_service),
) -> OrderOut:
    order = await service.get_order_by_id(order_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order with id {order_id} not found",
        )
    return order
