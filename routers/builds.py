from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel

from core.database import get_db
from models.build import Build
from models.cache import FarmAnalysis
from services.zenith import zenith_service

router = APIRouter(prefix="/builds", tags=["builds"])

class BuildCreate(BaseModel):
    zenith_url: str

class BuildResponse(BaseModel):
    id: int
    zenith_url: str
    zenith_id: str
    items_ids: List[int]
    created_at: str
    
    class Config:
        from_attributes = True

@router.post("/", response_model=BuildResponse)
async def create_build(build_data: BuildCreate, db: Session = Depends(get_db)):
    """Parse et sauvegarde un build Zenith"""
    
    # Parse le build depuis Zenith
    parsed_data = await zenith_service.parse_build(build_data.zenith_url)
    if not parsed_data:
        raise HTTPException(status_code=400, detail="Impossible de parser le build Zenith")
    
    # Vérifier si le build existe déjà
    existing_build = db.query(Build).filter(
        Build.zenith_url == build_data.zenith_url
    ).first()
    
    if existing_build:
        return existing_build
    
    # Créer le nouveau build
    db_build = Build(
        zenith_url=parsed_data["zenith_url"],
        zenith_id=parsed_data["zenith_id"],
        items_ids=parsed_data["items_ids"]
    )
    
    db.add(db_build)
    db.commit()
    db.refresh(db_build)
    
    return db_build

@router.get("/{build_id}", response_model=BuildResponse)
async def get_build(build_id: int, db: Session = Depends(get_db)):
    """Récupère un build par son ID"""
    build = db.query(Build).filter(Build.id == build_id).first()
    if not build:
        raise HTTPException(status_code=404, detail="Build non trouvé")
    return build

@router.get("/{build_id}/roadmap")
async def get_build_roadmap(build_id: int, db: Session = Depends(get_db)):
    """Génère la roadmap de farm pour un build"""
    build = db.query(Build).filter(Build.id == build_id).first()
    if not build:
        raise HTTPException(status_code=404, detail="Build non trouvé")
    
    # Récupère les analyses de farm pour ce build
    analyses = db.query(FarmAnalysis).filter(
        FarmAnalysis.build_id == build_id
    ).all()
    
    roadmap = {
        "build_id": build_id,
        "items_analysis": []
    }
    
    for analysis in analyses:
        roadmap["items_analysis"].append({
            "item_id": analysis.item_id,
            "obtention_type": analysis.obtention_type,
            "farm_data": analysis.farm_data
        })
    
    return roadmap