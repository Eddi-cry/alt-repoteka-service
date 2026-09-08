from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from src.api.main import app
from src.db.models import Branch, Package
from src.db.session import get_db


@pytest.fixture
async def mock_db_session():
    """Create a mock async database session."""
    session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.unique.return_value.all.return_value = []
    mock_result.scalars.return_value.all.return_value = []
    mock_result.scalar_one_or_none.return_value = None
    mock_result.all.return_value = []
    session.execute.return_value = mock_result
    yield session


@pytest.fixture
async def override_get_db(mock_db_session):
    """Override get_db dependency with mock session."""

    async def _override_get_db():
        yield mock_db_session

    app.dependency_overrides[get_db] = _override_get_db
    yield mock_db_session
    app.dependency_overrides.clear()


@pytest.fixture
async def async_client(override_get_db):
    """Create async test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.mark.asyncio
class TestMaintainerOutdatedEndpoint:
    """Tests for /api/maintainer-outdated endpoint."""

    async def test_maintainer_outdated_success(self, async_client, mock_db_session):
        """Test successful maintainer outdated packages query with JOIN optimization."""
        # Setup mocks
        mock_branch = MagicMock(spec=Branch)
        mock_branch.name = "p10"
        mock_branch.id = 1

        mock_sisyphus = MagicMock(spec=Branch)
        mock_sisyphus.name = "sisyphus"
        mock_sisyphus.id = 2

        mock_pkg = MagicMock(spec=Package)
        mock_pkg.name = "curl"
        mock_pkg.kind = "binary"
        mock_pkg.arch = "x86_64"
        mock_pkg.epoch = 0
        mock_pkg.version = "7.29.0"
        mock_pkg.release = "alt1"
        mock_pkg.branch = mock_branch

        mock_sisyphus_pkg = MagicMock(spec=Package)
        mock_sisyphus_pkg.epoch = 0
        mock_sisyphus_pkg.version = "8.0.0"
        mock_sisyphus_pkg.release = "alt1"

        # Mock results
        mock_branch_result = MagicMock()
        mock_branch_result.scalar_one_or_none.return_value = mock_branch

        mock_sisyphus_result = MagicMock()
        mock_sisyphus_result.scalar_one_or_none.return_value = mock_sisyphus

        mock_join_result = MagicMock()
        mock_join_result.all.return_value = [(mock_pkg, mock_sisyphus_pkg)]

        mock_db_session.execute.side_effect = [
            mock_branch_result,
            mock_sisyphus_result,
            mock_join_result,
        ]

        response = await async_client.get(
            "/api/maintainer-outdated",
            params={"branch": "p10", "maintainer_email": "ldv@altlinux.org"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["branch"] == "p10"
        assert data["maintainer"] == "ldv@altlinux.org"
        assert len(data["outdated_packages"]) == 1
        assert data["outdated_packages"][0]["name"] == "curl"
        assert data["outdated_packages"][0]["current"] == "7.29.0-alt1"
        assert data["outdated_packages"][0]["sisyphus"] == "8.0.0-alt1"
        assert data["count"] == 1

    async def test_maintainer_branch_not_found(self, async_client, mock_db_session):
        """Test 404 when branch doesn't exist."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

        response = await async_client.get(
            "/api/maintainer-outdated",
            params={"branch": "nonexistent", "maintainer_email": "test@altlinux.org"},
        )

        assert response.status_code == 404
        assert "Branch nonexistent not found" in response.json()["detail"]


@pytest.mark.asyncio
class TestOutdatedDaysEndpoint:
    """Tests for /api/outdated-days endpoint."""

    async def test_outdated_days_success(self, async_client, mock_db_session):
        """Test successful outdated days query with bulk optimization."""
        mock_sisyphus = MagicMock(spec=Branch)
        mock_sisyphus.name = "sisyphus"
        mock_sisyphus.id = 1

        mock_branch = MagicMock(spec=Branch)
        mock_branch.name = "p10"
        mock_branch.id = 2

        mock_branch_pkg = MagicMock(spec=Package)
        mock_branch_pkg.epoch = 0
        mock_branch_pkg.version = "7.29.0"
        mock_branch_pkg.release = "alt1"
        mock_branch_pkg.buildtime = datetime(2024, 1, 1)
        mock_branch_pkg.branch_id = 2
        mock_branch_pkg.name = "curl"

        mock_sisyphus_pkg = MagicMock(spec=Package)
        mock_sisyphus_pkg.epoch = 0
        mock_sisyphus_pkg.version = "8.0.0"
        mock_sisyphus_pkg.release = "alt1"
        mock_sisyphus_pkg.buildtime = datetime(2024, 6, 1)
        mock_sisyphus_pkg.name = "curl"

        mock_sisyphus_result = MagicMock()
        mock_sisyphus_result.scalar_one_or_none.return_value = mock_sisyphus

        mock_branches_result = MagicMock()
        mock_branches_result.scalars.return_value.all.return_value = [mock_branch]

        mock_branch_pkgs_result = MagicMock()
        mock_branch_pkgs_result.scalars.return_value.all.return_value = [mock_branch_pkg]

        mock_sisyphus_pkgs_result = MagicMock()
        mock_sisyphus_pkgs_result.scalars.return_value.all.return_value = [mock_sisyphus_pkg]

        mock_db_session.execute.side_effect = [
            mock_sisyphus_result,
            mock_branches_result,
            mock_branch_pkgs_result,
            mock_sisyphus_pkgs_result,
        ]

        response = await async_client.get(
            "/api/outdated-days", params=[("packages", "curl"), ("packages", "openssl")]
        )

        assert response.status_code == 200
        data = response.json()
        assert "curl" in data
        assert "p10" in data["curl"]
        assert "days" in data["curl"]["p10"]
        assert data["curl"]["p10"]["branch_version"] == "7.29.0-alt1"
        assert data["curl"]["p10"]["sisyphus_version"] == "8.0.0-alt1"
