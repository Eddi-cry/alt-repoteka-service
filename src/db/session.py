"""
Async database session management.
"""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from ..config import Settings

engine = None
async_session_maker = None


def init_db(settings: Settings):
    """
    Initialize async database engine and session maker.

    Args:
        settings: Application settings with database credentials
    """
    global engine, async_session_maker

    # Create async engine for PostgreSQL
    # Replace postgresql:// with postgresql+asyncpg://
    database_url = settings.database_url.replace("postgresql://", "postgresql+asyncpg://")

    engine = create_async_engine(
        database_url,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        echo=False,  # Set to True for SQL logging during development
    )

    async_session_maker = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for FastAPI endpoints to get async database session.

    Yields:
        AsyncSession: Database session

    Example:
        @app.get("/endpoint")
        async def endpoint(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(Model))
            return result.scalars().all()
    """
    if async_session_maker is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")

    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def create_tables():
    """
    Create all database tables.

    Should be called during application startup or in migrations.
    """
    from .models import Base

    if engine is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
