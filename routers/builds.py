from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel

from core.database import get_db
from models.build import Build
from models.cache import FarmAnalysis
# Zenith n'est plus utilisé - tout se fait via /search/build-from-text

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

class BuildCreateWithItems(BaseModel):
    build_name: str
    items_ids: List[int]

@router.post("/", response_model=BuildResponse)
async def create_build(build_data: BuildCreateWithItems, db: Session = Depends(get_db)):
    """
    Crée un build à partir d'une liste d'items
    Note: Utilisez /search/build-from-text pour créer depuis du texte
    """
    if not build_data.items_ids:
        raise HTTPException(status_code=400, detail="Liste d'items ne peut pas être vide")
    
    # Créer le build
    db_build = Build(
        zenith_url=None,  # Plus utilisé
        zenith_id=build_data.build_name,  # On utilise ce champ pour le nom
        items_ids=build_data.items_ids
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
    """
    Génère la roadmap de farm complète pour un build
    Indique quels monstres farmer, dans quelles zones, avec les taux de drop
    """
    build = db.query(Build).filter(Build.id == build_id).first()
    if not build:
        raise HTTPException(status_code=404, detail="Build non trouvé")
    
    # Utiliser le drop_manager pour générer la roadmap optimisée
    from services.drop_manager import drop_manager
    
    roadmap = drop_manager.get_farm_roadmap(build.items_ids)
    roadmap["build_id"] = build_id
    roadmap["zenith_url"] = build.zenith_url
    
    return roadmap

@router.post("/{build_id}/analyze")
async def analyze_build_complete(build_id: int, db: Session = Depends(get_db)):
    """
    Analyse complète d'un build: récupère les infos des items et génère la roadmap
    """
    build = db.query(Build).filter(Build.id == build_id).first()
    if not build:
        raise HTTPException(status_code=404, detail="Build non trouvé")
    
    from services.analysis import analysis_service
    
    # Analyser le build et générer les données de farm
    analysis_result = await analysis_service.analyze_build_for_farming(
        build_id=build_id,
        items_ids=build.items_ids
    )
    
    # Ajouter les données de drop des monstres
    from services.drop_manager import drop_manager
    drops_data = drop_manager.get_drops_for_items(build.items_ids)
    
    return {
        "build_id": build_id,
        "zenith_url": build.zenith_url,
        "items_count": len(build.items_ids),
        "analysis": analysis_result,
        "drops_data": drops_data
    }