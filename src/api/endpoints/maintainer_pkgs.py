from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from ...db.models import Branch, Package
from ...db.session import get_db
from ...utils.formatting import format_evr
from ...utils.version_compare import compare_evr

router = APIRouter()


@router.get("/api/maintainer-outdated")
async def get_maintainer_outdated_packages(
    branch: str = Query(..., description="Branch name"),
    maintainer_email: str = Query(..., description="Email maintainer"),
    db: AsyncSession = Depends(get_db),
):
    """
    Question #2: Show packages in a branch that are older than Sisyphus
    for a given maintainer.

    Optimized with JOIN to avoid N+1 query problem.
    """
    # Find the target branch
    stmt = select(Branch).where(Branch.name == branch)
    result = await db.execute(stmt)
    branch_obj = result.scalar_one_or_none()

    if not branch_obj:
        raise HTTPException(status_code=404, detail=f"Branch {branch} not found")

    # Find sisyphus branch
    stmt_sisyphus = select(Branch).where(Branch.name == "sisyphus")
    result_sisyphus = await db.execute(stmt_sisyphus)
    sisyphus = result_sisyphus.scalar_one_or_none()

    if not sisyphus:
        raise HTTPException(status_code=404, detail="Sisyphus branch not found")

    # Create aliases for clarity
    BranchPkg = aliased(Package)
    SisyphusPkg = aliased(Package)

    # Single query with JOIN - no N+1 problem!
    stmt_join = (
        select(BranchPkg, SisyphusPkg)
        .outerjoin(
            SisyphusPkg,
            and_(
                SisyphusPkg.branch_id == sisyphus.id,
                SisyphusPkg.name == BranchPkg.name,
                SisyphusPkg.kind == BranchPkg.kind,
            ),
        )
        .where(
            BranchPkg.branch_id == branch_obj.id,
            BranchPkg.maintainer_email == maintainer_email,
            BranchPkg.kind == "binary",
        )
    )

    result_join = await db.execute(stmt_join)
    pairs = result_join.all()

    outdated = []
    for branch_pkg, sisyphus_pkg in pairs:
        # Only compare if both packages exist
        if sisyphus_pkg:
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
                outdated.append(
                    {
                        "name": branch_pkg.name,
                        "current": format_evr(
                            branch_pkg.epoch, branch_pkg.version, branch_pkg.release
                        ),
                        "sisyphus": format_evr(
                            sisyphus_pkg.epoch, sisyphus_pkg.version, sisyphus_pkg.release
                        ),
                        "arch": branch_pkg.arch,
                    }
                )

    return {
        "branch": branch,
        "maintainer": maintainer_email,
        "outdated_packages": outdated,
        "count": len(outdated),
    }
