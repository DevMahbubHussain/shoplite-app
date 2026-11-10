from typing import Protocol
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order


class OrderRepositoryProtocol(Protocol):
    async def create(self, order: Order) -> Order: ...
    async def get_by_id(self, order_id: int) -> Order | None: ...
    async def update_status(self, order_id: int, status: str) -> Order | None: ...


class PostgresOrderRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, order: Order) -> Order:
        self.session.add(order)
        await self.session.commit()
        await self.session.refresh(order)
        return order

    async def get_by_id(self, order_id: int) -> Order | None:
        return await self.session.get(Order, order_id)

    async def update_status(self, order_id: int, status: str) -> Order | None:
        order = await self.session.get(Order, order_id)
        if order:
            order.status = status
            await self.session.commit()
            await self.session.refresh(order)
        return order
