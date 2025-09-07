from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel, Field
from datetime import datetime
import sys

from core.database import get_db
from models.build import Build
from models.cache import FarmAnalysis
# Zenith n'est plus utilisé - tout se fait via /search/build-from-text

router = APIRouter(prefix="/builds", tags=["builds"])

class BuildResponse(BaseModel):
    id: int
    build_name: str
    items_ids: List[int]
    created_at: datetime
    
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
        build_name=build_data.build_name,
        items_ids=build_data.items_ids
    )
    
    db.add(db_build)
    db.commit()
    db.refresh(db_build)
    
    return db_build

@router.get("/{build_id}")
async def get_build(build_id: int, db: Session = Depends(get_db)):
    """
    Récupère un build par son ID avec sa roadmap complète
    Retourne la même structure que /search/build-from-text
    """
    build = db.query(Build).filter(Build.id == build_id).first()
    if not build:
        raise HTTPException(status_code=404, detail="Build non trouvé")
    
    # Récupérer les détails des items depuis le cache
    from models.cache import CachedItem
    items_found = []
    items_missing = []
    
    for item_id in build.items_ids:
        cached_item = db.query(CachedItem).filter(CachedItem.wakfu_id == item_id).first()
        if cached_item:
            try:
                item_data = cached_item.data_json
                item_name = item_data.get('title', {}).get('fr', f'Item {item_id}') if isinstance(item_data, dict) else f'Item {item_id}'
                
                # Extraire les infos supplémentaires
                from routers.search import get_item_type, get_item_rarity
                level = item_data.get('definition', {}).get('item', {}).get('level') if isinstance(item_data, dict) else None
                item_type = get_item_type(item_data) if isinstance(item_data, dict) else None
                
                # Utiliser la rareté du CDN Wakfu
                rarity = get_item_rarity(item_data) if isinstance(item_data, dict) else None
                
                # Structure PLATE attendue par le frontend
                items_found.append({
                    'wakfu_id': item_id,
                    'name': item_name,
                    'level': level,
                    'item_type': item_type,
                    'rarity': rarity,
                    'match_score': 1.0,  # Score parfait car c'est un item exact du build
                    'obtention_type': cached_item.obtention_type
                })
            except Exception as e:
                items_missing.append(f'Item {item_id} (erreur de données)')
        else:
            items_missing.append(f'Item {item_id} (non trouvé en cache)')
    
    # Générer la roadmap avec le drop_manager
    from services.drop_manager import drop_manager
    roadmap = drop_manager.get_farm_roadmap(build.items_ids)
    
    return {
        'build_id': build_id,
        'build_name': build.build_name,
        'items_found': items_found,
        'items_missing': items_missing,
        'items_count': len(items_found),
        'missing_count': len(items_missing),
        'farm_roadmap': roadmap,
        'created_at': build.created_at
    }

@router.get("/{build_id}/roadmap")
async def get_build_roadmap(build_id: int, collapsed: bool = True, db: Session = Depends(get_db)):
    """
    Génère la roadmap de farm complète pour un build
    Indique quels monstres farmer, dans quelles zones, avec les taux de drop
    
    Args:
        build_id: ID du build
        collapsed: Si True, retourne les zones avec monstres cachés par défaut
    """
    build = db.query(Build).filter(Build.id == build_id).first()
    if not build:
        raise HTTPException(status_code=404, detail="Build non trouvé")
    
    # Utiliser le drop_manager pour générer la roadmap optimisée
    from services.drop_manager import drop_manager
    
    roadmap = drop_manager.get_farm_roadmap(build.items_ids)
    roadmap["build_id"] = build_id
    roadmap["build_name"] = build.build_name
    roadmap["collapsed_by_default"] = collapsed
    
    # Si collapsed est activé, marquer toutes les zones comme non-expandées
    if collapsed and 'zones_organized' in roadmap:
        for zone in roadmap['zones_organized']:
            zone['expanded'] = False
    
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
        "build_name": build.build_name,
        "items_count": len(build.items_ids),
        "analysis": analysis_result,
        "drops_data": drops_data
    }