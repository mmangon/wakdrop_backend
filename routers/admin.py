"""
Endpoints d'administration pour l'initialisation et la maintenance
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel

from core.database import get_db
from services.wakfu_cdn import wakfu_cdn
from services.analysis import analysis_service
# from services.selenium_scraper import WakfuSeleniumScraper  # Module supprimé
import asyncio
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])

class InitRequest(BaseModel):
    scrape_pages: int = 5
    headless: bool = True
    sync_cdn: bool = True

class InitStatus:
    """Singleton pour suivre le statut de l'initialisation"""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.is_running = False
            cls._instance.progress = {}
            cls._instance.errors = []
        return cls._instance

init_status = InitStatus()

@router.post("/initialize")
async def initialize_system(
    background_tasks: BackgroundTasks,
    request: InitRequest
):
    """
    🚀 Lance l'initialisation complète du système
    
    Cette opération:
    1. Synchronise les données du CDN Wakfu (items, recettes)
    2. Lance le scraping des monstres et leurs drops
    3. Prépare la base de données pour l'utilisation
    
    ⚠️ ATTENTION: Cette opération peut prendre 10-30 minutes selon le nombre de pages!
    """
    if init_status.is_running:
        raise HTTPException(
            status_code=409,
            detail="Une initialisation est déjà en cours"
        )
    
    async def run_initialization():
        init_status.is_running = True
        init_status.progress = {"step": "starting", "details": "Démarrage..."}
        init_status.errors = []
        
        try:
            # Étape 1: Synchronisation CDN
            if request.sync_cdn:
                init_status.progress = {"step": "cdn_sync", "details": "Synchronisation CDN..."}
                
                items = await wakfu_cdn.get_items()
                recipes = await wakfu_cdn.get_recipes()
                harvest_loots = await wakfu_cdn.get_harvest_loots()
                
                if items:
                    await analysis_service.update_items_cache(
                        items=items or [],
                        recipes=recipes or [],
                        harvest_loots=harvest_loots or []
                    )
                    init_status.progress["cdn_items"] = len(items) if items else 0
            
            # Étape 2: Scraping des monstres
            if request.scrape_pages > 0:
                init_status.progress = {
                    "step": "scraping",
                    "details": f"Scraping de {request.scrape_pages} pages...",
                    "total_pages": request.scrape_pages
                }
                
                scraper = WakfuSeleniumScraper(headless=request.headless)
                try:
                    monsters = scraper.scrape_all_monsters(1, request.scrape_pages)
                    
                    init_status.progress["monsters_found"] = len(monsters)
                    
                    # Import en base
                    init_status.progress["step"] = "importing"
                    init_status.progress["details"] = "Import en base de données..."
                    
                    results = scraper.import_to_database(monsters)
                    init_status.progress.update(results)
                    
                finally:
                    scraper.close()
            
            init_status.progress["step"] = "completed"
            init_status.progress["details"] = "Initialisation terminée avec succès!"
            
        except Exception as e:
            init_status.errors.append(str(e))
            init_status.progress["step"] = "error"
            init_status.progress["details"] = f"Erreur: {str(e)}"
            logger.error(f"Erreur initialisation: {e}")
            
        finally:
            init_status.is_running = False
            if 'wakfu_cdn' in locals():
                await wakfu_cdn.close()
    
    background_tasks.add_task(run_initialization)
    
    return {
        "message": "Initialisation lancée en arrière-plan",
        "estimated_time": f"{request.scrape_pages * 3} minutes environ",
        "check_status": "/admin/init-status"
    }

@router.get("/init-status")
async def get_initialization_status():
    """Récupère le statut de l'initialisation en cours"""
    return {
        "is_running": init_status.is_running,
        "progress": init_status.progress,
        "errors": init_status.errors
    }

@router.post("/quick-setup")
async def quick_setup(db: Session = Depends(get_db)):
    """
    ⚡ Setup rapide: synchronise seulement le CDN (sans scraping)
    
    Utile pour:
    - Tester rapidement l'application
    - Mettre à jour les données d'items
    - Préparer la base avant un import manuel
    """
    try:
        # Sync CDN uniquement
        items = await wakfu_cdn.get_items()
        recipes = await wakfu_cdn.get_recipes()
        harvest_loots = await wakfu_cdn.get_harvest_loots()
        
        results = {
            "items": len(items) if items else 0,
            "recipes": len(recipes) if recipes else 0,
            "harvest_loots": len(harvest_loots) if harvest_loots else 0
        }
        
        if items:
            await analysis_service.update_items_cache(
                items=items or [],
                recipes=recipes or [],
                harvest_loots=harvest_loots or []
            )
            results["status"] = "success"
            results["message"] = "CDN synchronisé avec succès"
        else:
            results["status"] = "warning"
            results["message"] = "Aucune donnée récupérée"
        
        return results
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await wakfu_cdn.close()

@router.post("/import-json")
async def import_json_data(
    file_path: str,
    db: Session = Depends(get_db)
):
    """
    📤 Importe des données de monstres depuis un fichier JSON
    
    Format attendu:
    [
        {
            "id": 123,
            "name": "Bouftou",
            "level": 10,
            "drops": [
                {"item_id": 456, "item_name": "Laine", "drop_rate": 25.0}
            ]
        }
    ]
    """
    try:
        import json
        
        with open(file_path, 'r', encoding='utf-8') as f:
            monsters = json.load(f)
        
        # from services.selenium_scraper import WakfuSeleniumScraper  # Module supprimé
        scraper = WakfuSeleniumScraper()
        results = scraper.import_to_database(monsters)
        scraper.close()
        
        return {
            "status": "success",
            "imported": results
        }
        
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Fichier non trouvé")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/system-info")
async def get_system_info(db: Session = Depends(get_db)):
    """📊 Récupère les informations système et statistiques"""
    from models.cache import CachedItem, MonsterDrop, CachedMonster
    from models.build import Build
    
    return {
        "database": {
            "cached_items": db.query(CachedItem).count(),
            "cached_monsters": db.query(CachedMonster).count(),
            "monster_drops": db.query(MonsterDrop).count(),
            "builds": db.query(Build).count()
        },
        "cdn": {
            "version": wakfu_cdn.version,
            "base_url": wakfu_cdn.base_url
        },
        "status": "ready" if db.query(CachedItem).count() > 0 else "needs_initialization"
    }