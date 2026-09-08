"""
Async package loader for fetching and storing ALT Linux repository metadata.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from ..config import Settings
from ..db.models import Base, Branch, Package
from .repoteka_client import RepotekaClient

logger = logging.getLogger(__name__)


class PackageLoader:
    """Async loader for fetching package metadata from Repoteka API."""

    def __init__(self, settings: Settings):
        self.settings = settings

        # Create async engine for PostgreSQL
        database_url = settings.database_url.replace("postgresql://", "postgresql+asyncpg://")

        self.engine = create_async_engine(
            database_url,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
            echo=False,
        )

        self.async_session_maker = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

        self.client = RepotekaClient(settings.repoteka_url)

    async def init_db(self):
        """Create all database tables."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def load_all_branches(self):
        """Load metadata and packages for all branches."""
        async with self.client as client:
            branches_data = await client.get_branches()
            total_branches = len(branches_data)
            logger.info(f"Found {total_branches} branches to load")

            for idx, branch_info in enumerate(branches_data, 1):
                branch_name = branch_info["branch"]
                logger.info(f"\n{'='*50}")
                logger.info(f"[{idx}/{total_branches}] Loading branch: {branch_name}")
                logger.info(f"{'='*50}")

                try:
                    # Load branch metadata
                    await self.load_branch_metadata(branch_info)
                    # Load branch packages (binary and source)
                    await self.load_branch_packages(client, branch_name)
                    logger.info(f"Branch {branch_name} loaded successfully!")
                except Exception as e:
                    logger.error(f"Failed to load branch {branch_name}: {e}")
                    continue

    async def load_branch_metadata(self, branch_info: Dict):
        """Load or update branch metadata."""
        async with self.async_session_maker() as session:
            # Find existing branch
            stmt = select(Branch).where(Branch.name == branch_info["branch"])
            result = await session.execute(stmt)
            branch = result.scalar_one_or_none()

            if not branch:
                branch = Branch(name=branch_info["branch"])
                session.add(branch)

            # Update branch metadata
            branch.label = branch_info.get("label")
            branch.archive = branch_info.get("archive")
            branch.arches = ",".join(branch_info.get("arches", []))
            branch.components = ",".join(branch_info.get("components", []))
            branch.binary_count = branch_info.get("binary_count", 0)
            branch.source_count = branch_info.get("source_count", 0)
            branch.last_loaded_at = datetime.now()

            await session.commit()

            logger.info(
                f"{branch.name}: binary_count={branch.binary_count}, "
                f"source_count={branch.source_count}"
            )

    async def load_branch_packages(self, client: RepotekaClient, branch_name: str):
        """Load all packages (binary and source) for a branch."""
        await self._load_packages_by_kind(client, branch_name, "binary")
        await self._load_packages_by_kind(client, branch_name, "source")

    async def _load_packages_by_kind(self, client: RepotekaClient, branch_name: str, kind: str):
        """Load packages of a specific type for a branch."""
        # Get branch and expected count
        async with self.async_session_maker() as session:
            stmt = select(Branch).where(Branch.name == branch_name)
            result = await session.execute(stmt)
            branch = result.scalar_one_or_none()

            if not branch:
                logger.error(f"Branch {branch_name} not found")
                return

            branch_id = branch.id
            expected_count = branch.binary_count if kind == "binary" else branch.source_count

            if expected_count is None or expected_count == 0:
                logger.warning(
                    f"Expected count for {branch_name} ({kind}) is " f"{expected_count}, skipping"
                )
                return

        total_loaded = 0
        chunk_count = 0

        logger.info(
            f"Loading {kind} packages for {branch_name}, " f"expected ~{expected_count} packages"
        )

        async for packages_chunk in client.iter_branch_packages(
            branch=branch_name, kind=kind, chunk_size=2000
        ):
            chunk_count += 1
            total_loaded += len(packages_chunk)

            # Save batch
            await self._save_packages_batch(
                branch_id, packages_chunk, branch_name, kind, total_loaded, chunk_count
            )

            # Stop if we reached expected count
            if total_loaded >= expected_count:
                logger.info(
                    f"{branch_name} ({kind}): reached expected count "
                    f"{expected_count} (processed {total_loaded}), stopping"
                )
                break

        logger.info(
            f"{branch_name} ({kind}): finished with {total_loaded} processed, "
            f"expected {expected_count}"
        )

    async def _save_packages_batch(
        self,
        branch_id: int,
        packages: List[Dict],
        branch_name: Optional[str] = None,
        kind: Optional[str] = None,
        total_loaded: int = 0,
        chunk_count: int = 0,
    ):
        """Save a batch of packages to the database."""
        async with self.async_session_maker() as session:
            added = 0
            updated = 0

            for pkg_data in packages:
                maintainer_email = self._extract_email(pkg_data.get("packager"))

                # Check if package exists
                stmt = select(Package).where(
                    Package.branch_id == branch_id,
                    Package.name == pkg_data["name"],
                    Package.arch == pkg_data.get("arch"),
                    Package.kind == pkg_data.get("kind", "binary"),
                )
                result = await session.execute(stmt)
                existing = result.scalar_one_or_none()

                if existing:
                    # Update existing package
                    existing.version = pkg_data["version"]
                    existing.release = pkg_data["release"]
                    existing.epoch = pkg_data.get("epoch")
                    existing.source_rpm = pkg_data.get("source_rpm")
                    existing.summary = pkg_data.get("summary")
                    existing.group = pkg_data.get("group")
                    existing.packager = pkg_data.get("packager")
                    existing.maintainer_email = maintainer_email
                    existing.buildtime = self._timestamp_to_datetime(pkg_data.get("buildtime"))
                    existing.component = pkg_data.get("component")
                    existing.updated_at = datetime.now()
                    updated += 1
                else:
                    # Create new package
                    pkg = Package(
                        branch_id=branch_id,
                        name=pkg_data["name"],
                        version=pkg_data["version"],
                        release=pkg_data["release"],
                        epoch=pkg_data.get("epoch"),
                        arch=pkg_data.get("arch"),
                        kind=pkg_data.get("kind", "binary"),
                        source_rpm=pkg_data.get("source_rpm"),
                        summary=pkg_data.get("summary"),
                        group=pkg_data.get("group"),
                        packager=pkg_data.get("packager"),
                        maintainer_email=maintainer_email,
                        buildtime=self._timestamp_to_datetime(pkg_data.get("buildtime")),
                        component=pkg_data.get("component"),
                    )
                    session.add(pkg)
                    added += 1

            await session.commit()

            if branch_name and kind:
                logger.info(
                    f"{branch_name} ({kind}): chunk #{chunk_count}, "
                    f"added {added}, updated {updated}, "
                    f"total processed {total_loaded}"
                )

            # Log milestone every 10,000 packages
            if total_loaded % 10000 < 2000 and total_loaded > 0:
                logger.info(f"{branch_name} ({kind}): total processed {total_loaded} packages")

    def _extract_email(self, packager: Optional[str]) -> Optional[str]:
        """Extract email from packager string."""
        if not packager:
            return None
        import re

        match = re.search(r"<([^>]+)>", packager)
        return match.group(1) if match else None

    def _timestamp_to_datetime(self, timestamp: Optional[int]) -> Optional[datetime]:
        """Convert Unix timestamp to datetime."""
        if timestamp:
            return datetime.fromtimestamp(timestamp)
        return None
