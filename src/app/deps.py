"""Dependencies for FastAPI routes."""
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession

from src.app.models.base import get_db


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Get database session dependency."""
    async for session in get_db():
        yield session

