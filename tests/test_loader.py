# tests/test_loader.py
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.config import Settings
from src.loader.main import PackageLoader


@pytest.mark.asyncio
async def test_loader_saves_new_package():
    """Тестирует, что loader корректно сохраняет новый пакет в БД."""
    # 1. Arrange
    settings = Settings()
    loader = PackageLoader(settings)

    # Мокаем сессию БД
    mock_session = AsyncMock()
    mock_session.add = MagicMock()

    # ИСПРАВЛЕНИЕ: Создаем обычный MagicMock для результата запроса
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None  # Пакета еще нет

    # Привязываем этот обычный мок к return_value асинхронного execute
    mock_session.execute.return_value = mock_result

    # Мокаем session_maker, чтобы он возвращал наш мок при async with
    loader.async_session_maker = MagicMock()
    loader.async_session_maker.return_value.__aenter__.return_value = mock_session

    test_packages = [
        {
            "name": "bash",
            "version": "5.1",
            "release": "alt1",
            "epoch": 0,
            "arch": "x86_64",
            "kind": "binary",
            "packager": "Ivan Ivanov <ivan@altlinux.org>",
            "buildtime": 1690000000,
        }
    ]

    # 2. Act
    await loader._save_packages_batch(
        branch_id=1,
        packages=test_packages,
        branch_name="p10",
        kind="binary",
        total_loaded=1,
        chunk_count=1,
    )

    # 3. Assert
    mock_session.commit.assert_awaited_once()
    assert mock_session.add.call_count == 1

    added_package = mock_session.add.call_args[0][0]
    assert added_package.name == "bash"
    assert added_package.maintainer_email == "ivan@altlinux.org"
