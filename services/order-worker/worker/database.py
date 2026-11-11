from datetime import datetime, timezone
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from worker.config import worker_settings

engine = create_async_engine(
    worker_settings.DATABASE_URL,
    pool_size=5,
    max_overflow=2,
    echo=False,
)

async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def update_order_status(order_id: int, status: str) -> bool:
    stmt = text(
        "UPDATE orders "
        "SET status = :status, "
        "    updated_at = :updated_at, "
        "    completed_at = CASE WHEN :is_completed THEN :updated_at ELSE completed_at END "
        "WHERE id = :order_id"
    )
    async with async_session_factory() as session:
        async with session.begin():
            result = await session.execute(
                stmt,
                {
                    "status": status,
                    "is_completed": status == "COMPLETED",
                    "updated_at": datetime.now(timezone.utc),
                    "order_id": order_id,
                },
            )
            return result.rowcount > 0


async def simulate_slow_query() -> None:
    async with async_session_factory() as session:
        await session.execute(text("SELECT pg_sleep(2)"))
