from typing import Protocol
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product


class ProductRepositoryProtocol(Protocol):
    async def get_all(self) -> list[Product]: ...
    async def get_by_id(self, product_id: int) -> Product | None: ...
    async def count(self) -> int: ...
    async def create(self, product: Product) -> Product: ...
    async def bulk_create(self, products: list[Product]) -> None: ...


class PostgresProductRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_all(self) -> list[Product]:
        stmt = select(Product).order_by(Product.id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(self, product_id: int) -> Product | None:
        return await self.session.get(Product, product_id)

    async def count(self) -> int:
        stmt = select(Product)
        result = await self.session.execute(stmt)
        return len(result.scalars().all())

    async def create(self, product: Product) -> Product:
        self.session.add(product)
        await self.session.commit()
        await self.session.refresh(product)
        return product

    async def bulk_create(self, products: list[Product]) -> None:
        self.session.add_all(products)
        await self.session.commit()
