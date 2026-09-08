from typing import Dict, List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...db.models import Branch, Package
from ...db.session import get_db
from ...utils.formatting import format_evr
from ...utils.version_compare import compare_evr

router = APIRouter()


@router.get("/api/outdated-days")
async def get_outdated_days(
    packages: List[str] = Query(..., description="List of packages to check"),
    db: AsyncSession = Depends(get_db),
):
    """
    Question #3: How many days source packages are outdated compared to Sisyphus.

    Optimized with bulk queries to avoid N*M query problem.
    """
    # Find sisyphus branch
    stmt = select(Branch).where(Branch.name == "sisyphus")
    result = await db.execute(stmt)
    sisyphus = result.scalar_one_or_none()

    if not sisyphus:
        raise HTTPException(status_code=404, detail="Sisyphus branch not found")

    # Get all other branches
    stmt_branches = select(Branch).where(Branch.name != "sisyphus")
    result_branches = await db.execute(stmt_branches)
    branches = result_branches.scalars().all()

    # Bulk fetch all branch packages in ONE query
    stmt_branch_pkgs = select(Package).where(
        Package.branch_id.in_([b.id for b in branches]),
        Package.name.in_(packages),
        Package.kind == "source",
    )
    result_branch_pkgs = await db.execute(stmt_branch_pkgs)
    branch_packages = result_branch_pkgs.scalars().all()

    # Create a lookup dict: {(branch_id, pkg_name): Package}
    branch_pkg_lookup: Dict[tuple, Package] = {
        (pkg.branch_id, pkg.name): pkg for pkg in branch_packages
    }

    # Bulk fetch all sisyphus packages in ONE query
    stmt_sisyphus_pkgs = select(Package).where(
        Package.branch_id == sisyphus.id, Package.name.in_(packages), Package.kind == "source"
    )
    result_sisyphus_pkgs = await db.execute(stmt_sisyphus_pkgs)
    sisyphus_packages = result_sisyphus_pkgs.scalars().all()

    # Create a lookup dict: {pkg_name: Package}
    sisyphus_pkg_lookup: Dict[str, Package] = {pkg.name: pkg for pkg in sisyphus_packages}

    # Now process all combinations using in-memory lookups
    result = {}
    for pkg_name in packages:
        result[pkg_name] = {}

        sisyphus_pkg = sisyphus_pkg_lookup.get(pkg_name)
        if not sisyphus_pkg:
            continue

        for branch in branches:
            branch_pkg = branch_pkg_lookup.get((branch.id, pkg_name))

            if branch_pkg:
                if (
                    compare_evr(
                        branch_pkg.epoch or 0,
                        branch_pkg.version,
                        branch_pkg.release,
                        sisyphus_pkg.epoch or 0,
                        sisyphus_pkg.version,
                        sisyphus_pkg.release,
                    )
                    < 0
                ):
                    days = None
                    if branch_pkg.buildtime and sisyphus_pkg.buildtime:
                        days = (sisyphus_pkg.buildtime - branch_pkg.buildtime).days
                    elif branch_pkg.updated_at and sisyphus_pkg.updated_at:
                        days = (sisyphus_pkg.updated_at - branch_pkg.updated_at).days

                    if days is not None:
                        result[pkg_name][branch.name] = {
                            "days": days,
                            "branch_version": format_evr(
                                branch_pkg.epoch, branch_pkg.version, branch_pkg.release
                            ),
                            "sisyphus_version": format_evr(
                                sisyphus_pkg.epoch, sisyphus_pkg.version, sisyphus_pkg.release
                            ),
                        }

    return result
