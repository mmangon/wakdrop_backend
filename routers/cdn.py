from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Dict

from core.database import get_db
from services.wakfu_cdn import wakfu_cdn
from models.cache import CachedItem
from services.analysis import analysis_service

router = APIRouter(prefix="/cdn", tags=["cdn"])

@router.post("/sync")
async def sync_cdn_data(background_tasks: BackgroundTasks):
    """Lance la synchronisation des données CDN en arrière-plan"""
    background_tasks.add_task(sync_wakfu_data)
    return {"message": "Synchronisation CDN lancée en arrière-plan"}

@router.get("/version")
async def get_cdn_version():
    """Récupère la version actuelle du CDN"""
    version = await wakfu_cdn.get_current_version()
    return {"version": version}

@router.get("/stats")
async def get_cache_stats(db: Session = Depends(get_db)):
    """Statistiques du cache local"""
    total_items = db.query(CachedItem).count()
    
    # Count par type d'obtention
    obtention_counts = {}
    for obtention_type in ["craft", "harvest", "shop", "treasure", "unknown"]:
        count = db.query(CachedItem).filter(
            CachedItem.obtention_type == obtention_type
        ).count()
        obtention_counts[obtention_type] = count
    
    return {
        "total_cached_items": total_items,
        "obtention_breakdown": obtention_counts
    }

async def sync_wakfu_data():
    """Fonction de synchronisation des données CDN"""
    try:
        print("Début synchronisation CDN Wakfu...")
        
        # Récupère les données du CDN
        items = await wakfu_cdn.get_items()
        recipes = await wakfu_cdn.get_recipes()
        harvest_loots = await wakfu_cdn.get_harvest_loots()
        
        if not items:
            print("Erreur: impossible de récupérer les items")
            return
        
        print(f"Récupéré {len(items)} items du CDN")
        
        # Analyse et sauvegarde en BDD
        await analysis_service.update_items_cache(items, recipes, harvest_loots)
        
        print("Synchronisation CDN terminée")
        
    except Exception as e:
        print(f"Erreur synchronisation CDN: {e}")
    finally:
        await wakfu_cdn.close()