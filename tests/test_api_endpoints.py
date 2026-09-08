from unittest.mock import MagicMock

import pytest

from src.db.models import Branch, Package


@pytest.mark.asyncio
async def test_package_status_endpoint(async_client, mock_db_session):
    """Тест эндпоинта /api/package-status и форматирования EVR."""
    # 1. Arrange (Подготовка данных)
    mock_branch = MagicMock(spec=Branch)
    mock_branch.name = "p10"

    mock_pkg = MagicMock(spec=Package)
    mock_pkg.name = "curl"
    mock_pkg.kind = "binary"
    mock_pkg.arch = "x86_64"
    mock_pkg.epoch = 0  # Важно: epoch = 0 не должен отображаться как "0:"
    mock_pkg.version = "8.21.0"
    mock_pkg.release = "alt1"
    mock_pkg.branch = mock_branch

    # Настраиваем мок так, чтобы он вернул наш пакет
    mock_result = MagicMock()
    mock_result.scalars.return_value.unique.return_value.all.return_value = [mock_pkg]
    mock_db_session.execute.return_value = mock_result

    # 2. Act (Вызов эндпоинта)
    response = await async_client.get(
        "/api/package-status",
        params={
            "package_name": "curl",
            "package_type": "binary",
            "target_epoch": 1,
            "target_version": "8.22.0",
            "target_release": "alt1",
        },
    )

    # 3. Assert (Проверка результатов)
    assert response.status_code == 200
    data = response.json()

    assert data["package"] == "curl"
    assert data["target"] == "1:8.22.0-alt1"  # Здесь epoch > 0, он должен быть

    # Самое главное: проверяем, что форматирование сработало и "0:" не добавился
    assert len(data["outdated_in"]) == 1
    assert data["outdated_in"][0]["current_version"] == "8.21.0-alt1"
    assert data["outdated_in"][0]["branch"] == "p10"


@pytest.mark.asyncio
async def test_maintainer_outdated_endpoint_not_found(async_client):
    """Тест обработки ошибки 404, если ветка не найдена."""
    response = await async_client.get(
        "/api/maintainer-outdated",
        params={"branch": "non_existent_branch", "maintainer_email": "test@altlinux.org"},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Branch non_existent_branch not found"
