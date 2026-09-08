from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from ...db.models import Package
from ...db.session import get_db
from ...utils.formatting import format_evr
from ...utils.version_compare import compare_evr

router = APIRouter()


@router.get("/api/package-status")
async def check_package_status(
    package_name: str = Query(..., description="Имя пакета"),
    package_type: str = Query("binary", description="Тип пакета: binary или source"),
    target_epoch: int = Query(0, description="Целевая эпоха"),
    target_version: str = Query(..., description="Целевая версия"),
    target_release: str = Query(..., description="Целевой релиз"),
    db: AsyncSession = Depends(get_db),
):
    """
    Question #1: Find branches where package version is older than target.
    """
    # Query packages with eager loading of branch relationship
    stmt = (
        select(Package)
        .options(joinedload(Package.branch))
        .where(Package.name == package_name, Package.kind == package_type)
    )
    result = await db.execute(stmt)
    packages = result.scalars().unique().all()

    outdated_branches = []
    for pkg in packages:
        is_older = (
            compare_evr(
                pkg.epoch or 0,
                pkg.version,
                pkg.release,
                target_epoch,
                target_version,
                target_release,
            )
            < 0
        )

        if is_older and pkg.branch:
            outdated_branches.append(
                {
                    "branch": pkg.branch.name,
                    "current_version": format_evr(pkg.epoch, pkg.version, pkg.release),
                    "arch": pkg.arch,
                }
            )

    return {
        "package": package_name,
        "type": package_type,
        "target": format_evr(target_epoch, target_version, target_release),
        "outdated_in": outdated_branches,
    }
