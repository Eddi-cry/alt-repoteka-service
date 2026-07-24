from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session, joinedload
from typing import List

from ...db.session import get_db
from ...db.models import Package, Branch
from ...utils.version_compare import compare_evr

router = APIRouter()

@router.get("/api/maintainer-outdated")
async def get_maintainer_outdated_packages(
    branch: str = Query(..., description="Branch name"),
    maintainer_email: str = Query(..., description="Email maintainer"),
    db: Session = Depends(get_db)
):
    branch_obj = db.query(Branch).filter(Branch.name == branch).first()
    if not branch_obj:
        raise HTTPException(status_code=404, detail=f"Branch {branch} not found")
    
    packages = db.query(Package).options(joinedload(Package.branch)).filter(
        Package.branch_id == branch_obj.id,
        Package.maintainer_email == maintainer_email,
        Package.kind == 'binary'
    ).all()
    
    sisyphus = db.query(Branch).filter(Branch.name == "sisyphus").first()
    if not sisyphus:
        raise HTTPException(status_code=404, detail="Sisyphus branch not found")
    
    outdated = []
    for pkg in packages:
        sisyphus_pkg = db.query(Package).filter(
            Package.branch_id == sisyphus.id,
            Package.name == pkg.name,
            Package.kind == 'binary'
        ).first()
        
        if sisyphus_pkg:
            if compare_evr(
                pkg.epoch or 0, pkg.version, pkg.release,
                sisyphus_pkg.epoch or 0, sisyphus_pkg.version, sisyphus_pkg.release
            ) < 0:
                outdated.append({
                    "name": pkg.name,
                    "current": f"{pkg.epoch}:{pkg.version}-{pkg.release}" if pkg.epoch else f"{pkg.version}-{pkg.release}",
                    "sisyphus": f"{sisyphus_pkg.epoch}:{sisyphus_pkg.version}-{sisyphus_pkg.release}" if sisyphus_pkg.epoch else f"{sisyphus_pkg.version}-{sisyphus_pkg.release}",
                    "arch": pkg.arch
                })
    
    return {
        "branch": branch,
        "maintainer": maintainer_email,
        "outdated_packages": outdated,
        "count": len(outdated)
    }