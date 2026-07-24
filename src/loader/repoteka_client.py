import aiohttp
import asyncio
from typing import List, Dict, Optional, AsyncIterator
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class RepotekaClient:
    def __init__(self, base_url: str = "https://rdb.altlinux.org/repoteka"):
        self.base_url = base_url
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, *args):
        await self.session.close()
    
     # Get a list of all branches
    async def get_branches(self) -> List[Dict]:
        async with self.session.get(f"{self.base_url}/branches") as resp:
            resp.raise_for_status()
            return await resp.json()
    
    async def get_branch_packages(
        self, 
        branch: str, 
        kind: str = "all",
        limit: int = 1000,
        offset: int = 0
    ) -> Dict:
        # Get pagination-enabled branch packages
        params = {
            "branch": branch,
            "kind": kind,
            "limit": limit,
            "offset": offset
        }
        async with self.session.get(
            f"{self.base_url}/packages", 
            params=params
        ) as resp:
            resp.raise_for_status()
            return await resp.json()
    
    async def iter_branch_packages(
        self, 
        branch: str, 
        kind: str = "all",
        chunk_size: int = 1000
    ) -> AsyncIterator[List[Dict]]:
        # An iterator for getting all packages of a branch in parts
        offset = 0
        while True:
            data = await self.get_branch_packages(
                branch=branch,
                kind=kind,
                limit=chunk_size,
                offset=offset
            )
            items = data.get('items', [])
            if not items:
                break
            yield items
            offset += len(items)
            # If you receive less than you requested, it means that this is the last page
            if len(items) < chunk_size:
                break
            await asyncio.sleep(0.1)  
    
    async def get_package_details(
        self,
        name: str,
        branch: str,
        kind: str = "all"
    ) -> Dict:
        # Get detailed package information
        params = {
            "branch": branch,
            "kind": kind
        }
        async with self.session.get(
            f"{self.base_url}/packages/{name}",
            params=params
        ) as resp:
            if resp.status == 404:
                return None
            resp.raise_for_status()
            return await resp.json()