from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime  

from ...db.session import get_db
from ...db.models import Package, Branch
from ...utils.version_compare import compare_evr

router = APIRouter()

@router.get("/api/outdated-days")
async def get_outdated_days(
    packages: List[str] = Query(..., description="List of packages to check"),
    db: Session = Depends(get_db)
):
    sisyphus = db.query(Branch).filter(Branch.name == "sisyphus").first()
    if not sisyphus:
        raise HTTPException(status_code=404, detail="Sisyphus branch not found")
    
    branches = db.query(Branch).filter(Branch.name != "sisyphus").all()
    
    result = {}
    for pkg_name in packages:
        result[pkg_name] = {}
        
        for branch in branches:
            branch_pkg = db.query(Package).filter(
                Package.branch_id == branch.id,
                Package.name == pkg_name,
                Package.kind == 'source'
            ).first()
            
            sisyphus_pkg = db.query(Package).filter(
                Package.branch_id == sisyphus.id,
                Package.name == pkg_name,
                Package.kind == 'source'
            ).first()
            
            if branch_pkg and sisyphus_pkg:
                if compare_evr(
                    branch_pkg.epoch or 0, branch_pkg.version, branch_pkg.release,
                    sisyphus_pkg.epoch or 0, sisyphus_pkg.version, sisyphus_pkg.release
                ) < 0:
                    days = None
                    if branch_pkg.buildtime and sisyphus_pkg.buildtime:
                        days = (sisyphus_pkg.buildtime - branch_pkg.buildtime).days
                    elif branch_pkg.updated_at and sisyphus_pkg.updated_at:
                        days = (sisyphus_pkg.updated_at - branch_pkg.updated_at).days
                    
                    if days is not None:
                        result[pkg_name][branch.name] = {
                            "days": days,
                            "branch_version": f"{branch_pkg.epoch}:{branch_pkg.version}-{branch_pkg.release}" if branch_pkg.epoch else f"{branch_pkg.version}-{branch_pkg.release}",
                            "sisyphus_version": f"{sisyphus_pkg.epoch}:{sisyphus_pkg.version}-{sisyphus_pkg.release}" if sisyphus_pkg.epoch else f"{sisyphus_pkg.version}-{sisyphus_pkg.release}"
                        }
    
    return result