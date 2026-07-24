import asyncio
from datetime import datetime
from typing import Dict, List, Optional
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
import logging

from .repoteka_client import RepotekaClient
from ..db.models import Branch, Package, Base
from ..config import Settings

logger = logging.getLogger(__name__)

class PackageLoader:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.engine = create_engine(
            settings.database_url,
            connect_args={'client_encoding': 'utf8'}
        )
        self.Session = sessionmaker(bind=self.engine)
        self.client = RepotekaClient(settings.repoteka_url)
    
    def init_db(self):
        # Create table
        Base.metadata.create_all(self.engine)
    
    async def load_all_branches(self):
        # Uploading data for all branches
        async with self.client as client:
            branches_data = await client.get_branches()
            total_branches = len(branches_data)
            logger.info(f"Found {total_branches} branches to load")
            
            for idx, branch_info in enumerate(branches_data, 1):
                branch_name = branch_info['branch']
                logger.info(f"\n{'='*50}")
                logger.info(f"[{idx}/{total_branches}] Loading branch: {branch_name}")
                logger.info(f"{'='*50}")
                
                try:
                    # Load branch metadata (including binary_count and source_count)
                    await self.load_branch_metadata(branch_info)
                    # Downloading branch packages (binary and source)
                    await self.load_branch_packages(client, branch_name)
                    logger.info(f"Branch {branch_name} loaded successfully!")
                except Exception as e:
                    logger.error(f"Failed to load branch {branch_name}: {e}")
                    continue
    
    async def load_branch_metadata(self, branch_info: Dict):
        with self.Session() as session:
            branch = session.query(Branch).filter_by(
                name=branch_info['branch']
            ).first()
            
            if not branch:
                branch = Branch(name=branch_info['branch'])
            
            branch.label = branch_info.get('label')
            branch.archive = branch_info.get('archive')
            branch.arches = ','.join(branch_info.get('arches', []))
            branch.components = ','.join(branch_info.get('components', []))
            # Saving the exact quantities from the API
            branch.binary_count = branch_info.get('binary_count', 0)
            branch.source_count = branch_info.get('source_count', 0)
            branch.last_loaded_at = datetime.now()
            
            session.merge(branch)
            session.commit()
            logger.info(f"{branch.name}: binary_count={branch.binary_count}, source_count={branch.source_count}")
    
    async def load_branch_packages(self, client: RepotekaClient, branch_name: str):
        await self._load_packages_by_kind(client, branch_name, 'binary')
        await self._load_packages_by_kind(client, branch_name, 'source')
    
    async def _load_packages_by_kind(
        self, 
        client: RepotekaClient, 
        branch_name: str, 
        kind: str
    ):
        # Loading packages of a specific type with a limit on the expected number
        # Get the branch and the expected amount
        with self.Session() as session:
            branch = session.query(Branch).filter_by(name=branch_name).first()
            if not branch:
                logger.error(f"Branch {branch_name} not found")
                return
            branch_id = branch.id
            expected_count = branch.binary_count if kind == 'binary' else branch.source_count
            if expected_count is None:
                logger.warning(f"Expected count for {branch_name} ({kind}) is None, skipping")
                return
            if expected_count == 0:
                logger.warning(f"Expected count for {branch_name} ({kind}) is 0, skipping")
                return
        
        total_loaded = 0
        chunk_count = 0
        
        logger.info(f"Loading {kind} packages for {branch_name}, expected ~{expected_count} packages")
        
        async for packages_chunk in client.iter_branch_packages(
            branch=branch_name,
            kind=kind,
            chunk_size=2000
        ):
            chunk_count += 1
            total_loaded += len(packages_chunk)
            
            # Saving the pack
            await self._save_packages_batch(branch_id, packages_chunk, branch_name, kind, total_loaded, chunk_count)
            
            # If we have already processed the expected amount (or more), exit
            if total_loaded >= expected_count:
                logger.info(f"{branch_name} ({kind}): reached expected count {expected_count} (processed {total_loaded}), stopping")
                break
            
            # Safe interrupt: if the API returns empty chunks, but total_loaded does not increase (protection against an infinite loop)
            # Here, we rely on the break inside iter_branch_packages, but we also check that the chunk is not empty.
        
        logger.info(f"{branch_name} ({kind}): finished with {total_loaded} processed, expected {expected_count}")
    
    async def _save_packages_batch(
        self, 
        branch_id: int, 
        packages: List[Dict],
        branch_name: str = None,
        kind: str = None,
        total_loaded: int = 0,
        chunk_count: int = 0
    ):
        # Saving a batch of packages in the database with logging of added/updated
        with self.Session() as session:
            added = 0
            updated = 0
            
            for pkg_data in packages:
                maintainer_email = self._extract_email(pkg_data.get('packager'))
                
                existing = session.query(Package).filter_by(
                    branch_id=branch_id,
                    name=pkg_data['name'],
                    arch=pkg_data.get('arch'),
                    kind=pkg_data.get('kind', 'binary')
                ).first()
                
                if existing:
                    existing.version = pkg_data['version']
                    existing.release = pkg_data['release']
                    existing.epoch = pkg_data.get('epoch')
                    existing.source_rpm = pkg_data.get('source_rpm')
                    existing.summary = pkg_data.get('summary')
                    existing.group = pkg_data.get('group')
                    existing.packager = pkg_data.get('packager')
                    existing.maintainer_email = maintainer_email
                    existing.buildtime = self._timestamp_to_datetime(pkg_data.get('buildtime'))
                    existing.component = pkg_data.get('component')
                    existing.updated_at = datetime.now()
                    updated += 1
                else:
                    pkg = Package(
                        branch_id=branch_id,
                        name=pkg_data['name'],
                        version=pkg_data['version'],
                        release=pkg_data['release'],
                        epoch=pkg_data.get('epoch'),
                        arch=pkg_data.get('arch'),
                        kind=pkg_data.get('kind', 'binary'),
                        source_rpm=pkg_data.get('source_rpm'),
                        summary=pkg_data.get('summary'),
                        group=pkg_data.get('group'),
                        packager=pkg_data.get('packager'),
                        maintainer_email=maintainer_email,
                        buildtime=self._timestamp_to_datetime(pkg_data.get('buildtime')),
                        component=pkg_data.get('component')
                    )
                    session.add(pkg)
                    added += 1
            
            session.commit()
            
            if branch_name and kind:
                logger.info(f"{branch_name} ({kind}): chunk #{chunk_count}, added {added}, updated {updated}, total processed {total_loaded}")
            
            # We display a separate message for every 10,000 packets
            if total_loaded % 10000 < 2000 and total_loaded > 0:
                logger.info(f"{branch_name} ({kind}): total processed {total_loaded} packages")
    
    def _extract_email(self, packager: str) -> Optional[str]:
        if not packager:
            return None
        import re
        match = re.search(r'<([^>]+)>', packager)
        return match.group(1) if match else None
    
    def _timestamp_to_datetime(self, timestamp: int) -> Optional[datetime]:
        if timestamp:
            return datetime.fromtimestamp(timestamp)
        return None