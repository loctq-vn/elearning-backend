import sys
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings

_use_null_pool = "pytest" in sys.modules or any("pytest" in arg for arg in sys.argv)
engine = create_async_engine(
    settings.database_url,
    pool_pre_ping=True,
    poolclass=NullPool if _use_null_pool else None,
)
async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        yield session
