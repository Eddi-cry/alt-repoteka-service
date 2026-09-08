# tests/conftest.py
from unittest.mock import AsyncMock, MagicMock

import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.api.main import app
from src.db.session import get_db


@pytest_asyncio.fixture
async def mock_db_session():
    """Создает надежный мок-объект сессии БД для тестов."""
    session = AsyncMock()

    # ИСПРАВЛЕНИЕ: Делаем синхронные методы обычными MagicMock
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_result.scalars.return_value.unique.return_value.all.return_value = []

    session.execute.return_value = mock_result
    yield session


@pytest_asyncio.fixture
async def override_get_db(mock_db_session):
    """Подменяет зависимость get_db в FastAPI на нашу мок-сессию."""

    async def _override_get_db():
        yield mock_db_session

    app.dependency_overrides[get_db] = _override_get_db
    yield mock_db_session
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def async_client(override_get_db):
    """Асинхронный клиент для тестирования API."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
