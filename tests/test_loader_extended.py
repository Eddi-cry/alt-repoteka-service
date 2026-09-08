from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.config import Settings
from src.loader.main import PackageLoader
from src.loader.repoteka_client import RepotekaClient


@pytest.fixture
def settings():
    """Create test settings."""
    return Settings(
        db_host="localhost",
        db_port=5432,
        db_name="test_repoteka",
        db_user="test_user",
        db_password="test_pass",
        repoteka_url="https://test.repoteeka.org",
    )


@pytest.fixture
def mock_loader(settings):
    """Create a PackageLoader with properly mocked async dependencies."""
    loader = PackageLoader(settings)

    # 1. Сессия должна поддерживать async with
    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)

    # 2. ВАЖНО: Результат execute() должен быть ОБЫЧНЫМ MagicMock!
    # Потому что в коде мы делаем: result = await session.execute(),
    # а затем result.scalar_one_or_none() вызывается СИНХРОННО.
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None  # Значение по умолчанию

    # Связываем execute с обычным моком
    mock_session.execute.return_value = mock_result

    # 3. session_maker возвращает сессию синхронно
    mock_session_maker = MagicMock(return_value=mock_session)
    loader.async_session_maker = mock_session_maker

    return loader


class TestPackageLoader:
    """Tests for PackageLoader class."""

    @pytest.mark.asyncio
    async def test_init_db_creates_tables(self, mock_loader):
        """Test that init_db creates all tables."""
        mock_conn = AsyncMock()
        mock_conn.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_conn.__aexit__ = AsyncMock(return_value=None)

        mock_engine = AsyncMock()
        mock_engine.begin = MagicMock(return_value=mock_conn)

        mock_loader.engine = mock_engine

        await mock_loader.init_db()
        mock_engine.begin.assert_called_once()

    @pytest.mark.asyncio
    async def test_load_branch_metadata_new_branch(self, mock_loader):
        """Test loading metadata for a new branch."""
        # Убеждаемся, что ветка не найдена (возвращает None)
        mock_loader.async_session_maker.return_value.execute.return_value.scalar_one_or_none.return_value = (
            None
        )

        branch_info = {
            "branch": "p10",
            "label": "Platform 10",
            "archive": True,
            "arches": ["x86_64", "i586"],
            "components": ["main", "contrib"],
            "binary_count": 1000,
            "source_count": 200,
        }

        await mock_loader.load_branch_metadata(branch_info)

        mock_session = mock_loader.async_session_maker.return_value
        assert mock_session.add.called
        mock_session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_load_branch_metadata_existing_branch(self, mock_loader):
        """Test updating metadata for an existing branch."""
        mock_branch = MagicMock()
        mock_branch.name = "p10"
        mock_branch.binary_count = 500
        mock_branch.source_count = 100

        # Настраиваем мок так, чтобы он вернул существующую ветку
        mock_loader.async_session_maker.return_value.execute.return_value.scalar_one_or_none.return_value = (
            mock_branch
        )

        branch_info = {"branch": "p10", "binary_count": 1000, "source_count": 200}

        await mock_loader.load_branch_metadata(branch_info)

        assert mock_branch.binary_count == 1000
        mock_session = mock_loader.async_session_maker.return_value
        mock_session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_save_packages_batch_new_packages(self, mock_loader):
        """Test saving a batch of new packages."""
        mock_loader.async_session_maker.return_value.execute.return_value.scalar_one_or_none.return_value = (
            None
        )

        packages = [
            {
                "name": "curl",
                "version": "7.29.0",
                "release": "alt1",
                "epoch": 0,
                "arch": "x86_64",
                "kind": "binary",
                "packager": "Ivan Ivanov <ivan@altlinux.org>",
                "buildtime": 1690000000,
                "group": "Networking",
                "component": "main",
            }
        ]

        await mock_loader._save_packages_batch(
            branch_id=1,
            packages=packages,
            branch_name="p10",
            kind="binary",
            total_loaded=1,
            chunk_count=1,
        )

        mock_session = mock_loader.async_session_maker.return_value
        assert mock_session.add.called
        mock_session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_save_packages_batch_update_existing(self, mock_loader):
        """Test updating existing packages."""
        mock_existing_pkg = MagicMock()
        mock_existing_pkg.version = "7.28.0"
        mock_existing_pkg.release = "alt1"

        mock_loader.async_session_maker.return_value.execute.return_value.scalar_one_or_none.return_value = (
            mock_existing_pkg
        )

        packages = [
            {
                "name": "curl",
                "version": "7.29.0",
                "release": "alt1",
                "epoch": 0,
                "arch": "x86_64",
                "kind": "binary",
                "packager": "Ivan Ivanov <ivan@altlinux.org>",
                "buildtime": 1690000000,
            }
        ]

        await mock_loader._save_packages_batch(
            branch_id=1,
            packages=packages,
            branch_name="p10",
            kind="binary",
            total_loaded=1,
            chunk_count=1,
        )

        assert mock_existing_pkg.version == "7.29.0"
        mock_session = mock_loader.async_session_maker.return_value
        mock_session.commit.assert_awaited_once()

    # Синхронные тесты без @pytest.mark.asyncio
    def test_extract_email(self, mock_loader):
        """Test email extraction from packager string."""
        assert mock_loader._extract_email("Ivan Ivanov <ivan@altlinux.org>") == "ivan@altlinux.org"
        assert mock_loader._extract_email("No Email") is None
        assert mock_loader._extract_email(None) is None
        assert mock_loader._extract_email("") is None

    def test_timestamp_to_datetime(self, mock_loader):
        """Test timestamp to datetime conversion."""
        dt = mock_loader._timestamp_to_datetime(1690000000)
        assert isinstance(dt, datetime)
        assert dt.year == 2023

        assert mock_loader._timestamp_to_datetime(None) is None
        assert mock_loader._timestamp_to_datetime(0) is None


@pytest.mark.asyncio
class TestRepotekaClient:
    """Tests for RepotekaClient class."""

    async def test_get_branches_success(self):
        """Test successful branches fetch."""
        client = RepotekaClient()

        mock_response = AsyncMock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        mock_response.raise_for_status = MagicMock()
        mock_response.json = AsyncMock(
            return_value=[{"branch": "p10", "binary_count": 1000, "source_count": 200}]
        )

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_response)
        client.session = mock_session

        branches = await client.get_branches()

        assert len(branches) == 1
        assert branches[0]["branch"] == "p10"

    async def test_get_branch_packages_pagination(self):
        """Test package fetching with pagination."""
        client = RepotekaClient()

        mock_response = AsyncMock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        mock_response.raise_for_status = MagicMock()
        mock_response.json = AsyncMock(
            return_value={"items": [{"name": "curl", "version": "7.29.0"}], "total": 1}
        )

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=mock_response)
        client.session = mock_session

        packages = await client.get_branch_packages("p10", "binary", limit=100, offset=0)

        assert len(packages["items"]) == 1
