from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session, joinedload
from typing import List

from ...db.session import get_db
from ...db.models import Package, Branch
from ...utils.version_compare import compare_evr

router = APIRouter()

@router.get("/api/package-status")
async def check_package_status(
    package_name: str = Query(..., description="Имя пакета"),
    package_type: str = Query("binary", description="Тип пакета: binary или source"),
    target_epoch: int = Query(0, description="Целевая эпоха"),
    target_version: str = Query(..., description="Целевая версия"),
    target_release: str = Query(..., description="Целевой релиз"),
    db: Session = Depends(get_db)
):
    # Question #1: Find the branches where the package version is behind the specified version

    # Use joinedload to load a linked branch
    packages = db.query(Package).options(joinedload(Package.branch)).filter(
        Package.name == package_name,
        Package.kind == package_type
    ).all()
    
    outdated_branches = []
    for pkg in packages:
        is_older = compare_evr(
            pkg.epoch or 0, pkg.version, pkg.release,
            target_epoch, target_version, target_release
        ) < 0
        
        if is_older and pkg.branch:
            outdated_branches.append({
                "branch": pkg.branch.name,
                "current_version": f"{pkg.epoch}:{pkg.version}-{pkg.release}" if pkg.epoch else f"{pkg.version}-{pkg.release}",
                "arch": pkg.arch
            })
    
    return {
        "package": package_name,
        "type": package_type,
        "target": f"{target_epoch}:{target_version}-{target_release}",
        "outdated_in": outdated_branches
    }