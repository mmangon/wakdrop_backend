"""
Endpoints API pour gérer les données de drop des monstres
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from core.database import get_db
from models.cache import MonsterDrop, CachedMonster
from services.drop_manager import drop_manager
# from services.selenium_scraper import WakfuSeleniumScraper  # Module supprimé
import asyncio

router = APIRouter(prefix="/drops", tags=["drops"])

class DropResponse(BaseModel):
    monster_id: int
    monster_name: str
    monster_level: Optional[int]
    item_id: int
    drop_rate: float
    zone_name: Optional[str]
    
    class Config:
        from_attributes = True

class FarmRoadmapRequest(BaseModel):
    item_ids: List[int]

class ScrapeRequest(BaseModel):
    start_page: int = 1
    end_page: int = 1
    headless: bool = True

class ImportItemsRequest(BaseModel):
    item_ids: List[int]

@router.get("/item/{item_id}", response_model=List[DropResponse])
async def get_item_drops(item_id: int, db: Session = Depends(get_db)):
    """Récupère tous les monstres qui drop un item spécifique"""
    drops = db.query(MonsterDrop).filter(
        MonsterDrop.item_id == item_id
    ).order_by(MonsterDrop.drop_rate.desc()).all()
    
    if not drops:
        raise HTTPException(status_code=404, detail="Aucun drop trouvé pour cet item")
    
    return drops

@router.get("/monster/{monster_id}")
async def get_monster_drops(monster_id: int, db: Session = Depends(get_db)):
    """Récupère tous les items droppés par un monstre"""
    drops = db.query(MonsterDrop).filter(
        MonsterDrop.monster_id == monster_id
    ).order_by(MonsterDrop.drop_rate.desc()).all()
    
    if not drops:
        raise HTTPException(status_code=404, detail="Aucun drop trouvé pour ce monstre")
    
    # Récupérer les infos du monstre
    monster = db.query(CachedMonster).filter(
        CachedMonster.wakfu_id == monster_id
    ).first()
    
    return {
        "monster": {
            "id": monster_id,
            "name": monster.name if monster else "Unknown",
            "level": monster.level if monster else None
        },
        "drops": [
            {
                "item_id": drop.item_id,
                "drop_rate": drop.drop_rate
            } for drop in drops
        ]
    }

@router.post("/farm-roadmap")
async def generate_farm_roadmap(request: FarmRoadmapRequest):
    """
    Génère une roadmap de farm optimisée pour une liste d'items
    
    La roadmap indique:
    - Quels monstres farmer
    - Dans quelles zones
    - Les taux de drop pour optimiser le farm
    """
    if not request.item_ids:
        raise HTTPException(status_code=400, detail="La liste d'items est vide")
    
    roadmap = drop_manager.get_farm_roadmap(request.item_ids)
    
    if not roadmap.get('monsters'):
        raise HTTPException(
            status_code=404, 
            detail="Aucune donnée de drop trouvée pour ces items. Lancez d'abord un scraping."
        )
    
    return roadmap

@router.post("/scrape")
async def scrape_monsters(
    background_tasks: BackgroundTasks,
    request: ScrapeRequest
):
    """
    Lance le scraping des données de drop depuis l'encyclopédie Wakfu
    
    ⚠️ ATTENTION: Cette opération peut prendre du temps!
    - 1 page ≈ 20 monstres ≈ 2-3 minutes
    - Le scraping se fait en arrière-plan
    """
    async def run_scraping():
        from services.improved_scraper import ImprovedScraper
        from models.cache import MonsterDrop, CachedMonster
        from sqlalchemy import and_
        
        scraper = ImprovedScraper(delay_min=1.0, delay_max=2.0)
        db = SessionLocal()
        
        try:
            # Scraper les monstres
            monsters = await scraper.scrape_monsters(request.start_page, request.end_page)
            
            # Import en base de données
            results = {'monsters_added': 0, 'drops_added': 0, 'drops_updated': 0, 'errors': []}
            
            for monster in monsters:
                try:
                    monster_id = monster['id']
                    
                    # Monstre en cache
                    cached_monster = db.query(CachedMonster).filter(
                        CachedMonster.wakfu_id == monster_id
                    ).first()
                    
                    if not cached_monster:
                        cached_monster = CachedMonster(
                            wakfu_id=monster_id,
                            name=monster['name'],
                            level=monster.get('level'),
                            data_json=monster
                        )
                        db.add(cached_monster)
                        results['monsters_added'] += 1
                    
                    # Drops
                    for drop in monster.get('drops', []):
                        existing = db.query(MonsterDrop).filter(
                            and_(
                                MonsterDrop.monster_id == monster_id,
                                MonsterDrop.item_id == drop['item_id']
                            )
                        ).first()
                        
                        if existing:
                            if existing.drop_rate != drop['drop_rate']:
                                existing.drop_rate = drop['drop_rate']
                                results['drops_updated'] += 1
                        else:
                            new_drop = MonsterDrop(
                                monster_id=monster_id,
                                monster_name=monster['name'],
                                monster_level=monster.get('level'),
                                item_id=drop['item_id'],
                                drop_rate=drop['drop_rate']
                            )
                            db.add(new_drop)
                            results['drops_added'] += 1
                    
                    db.commit()
                
                except Exception as e:
                    db.rollback()
                    results['errors'].append(f"{monster.get('name', 'Unknown')}: {str(e)}")
            
            return results
            
        finally:
            await scraper.close()
            db.close()
    
    background_tasks.add_task(run_scraping)
    
    return {
        "message": f"Scraping lancé pour les pages {request.start_page} à {request.end_page}",
        "status": "Le scraping s'exécute en arrière-plan",
        "estimated_time": f"~{(request.end_page - request.start_page + 1) * 2} minutes"
    }

class ImportDropsRequest(BaseModel):
    monsters: List[dict]

@router.post("/import")
async def import_monster_drops(request: ImportDropsRequest, db: Session = Depends(get_db)):
    """
    Importe les données de drop depuis un script externe
    
    Format attendu:
    {
        "monsters": [
            {
                "id": 123,
                "name": "Nom du Monstre",
                "level": 50,
                "zone": "Zone Name",
                "drops": [
                    {"item_id": 456, "item_name": "Item", "drop_rate": 15.5},
                    ...
                ]
            },
            ...
        ]
    }
    """
    from sqlalchemy import and_
    
    results = {
        'monsters_processed': 0,
        'monsters_added': 0,
        'drops_added': 0,
        'drops_updated': 0,
        'errors': []
    }
    
    try:
        for monster_data in request.monsters:
            try:
                monster_id = monster_data.get('id')
                monster_name = monster_data.get('name', 'Unknown')
                
                if not monster_id:
                    results['errors'].append(f"Monstre sans ID ignoré: {monster_name}")
                    continue
                
                results['monsters_processed'] += 1
                
                # Vérifier/créer le monstre en cache
                cached_monster = db.query(CachedMonster).filter(
                    CachedMonster.wakfu_id == monster_id
                ).first()
                
                if not cached_monster:
                    cached_monster = CachedMonster(
                        wakfu_id=monster_id,
                        name=monster_name,
                        level=monster_data.get('level'),
                        data_json={
                            'name': monster_name,
                            'level': monster_data.get('level'),
                            'zone': monster_data.get('zone'),
                            'imported_at': str(datetime.utcnow())
                        }
                    )
                    db.add(cached_monster)
                    results['monsters_added'] += 1
                
                # Traiter les drops
                for drop_data in monster_data.get('drops', []):
                    item_id = drop_data.get('item_id')
                    drop_rate = drop_data.get('drop_rate', 0.0)
                    
                    if not item_id:
                        continue
                    
                    # Vérifier si le drop existe déjà
                    existing_drop = db.query(MonsterDrop).filter(
                        and_(
                            MonsterDrop.monster_id == monster_id,
                            MonsterDrop.item_id == item_id
                        )
                    ).first()
                    
                    if existing_drop:
                        # Mettre à jour si différent
                        if existing_drop.drop_rate != drop_rate:
                            existing_drop.drop_rate = drop_rate
                            existing_drop.zone_name = monster_data.get('zone')
                            results['drops_updated'] += 1
                    else:
                        # Créer nouveau drop
                        new_drop = MonsterDrop(
                            monster_id=monster_id,
                            monster_name=monster_name,
                            monster_level=monster_data.get('level'),
                            item_id=item_id,
                            drop_rate=drop_rate,
                            zone_name=monster_data.get('zone')
                        )
                        db.add(new_drop)
                        results['drops_added'] += 1
                
                db.commit()
                
            except Exception as e:
                db.rollback()
                results['errors'].append(f"Erreur monstre {monster_data.get('name', 'Unknown')}: {str(e)}")
                continue
        
        return {
            "message": "Import terminé",
            "results": results
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erreur import: {str(e)}")

@router.post("/import-items")
async def import_items_drops(
    background_tasks: BackgroundTasks,
    request: ImportItemsRequest
):
    """
    Importe les données de drop pour une liste spécifique d'items
    
    Plus rapide que le scraping complet si vous ne voulez que certains items
    """
    async def import_task():
        return await drop_manager.import_drops_from_scraper(request.item_ids)
    
    background_tasks.add_task(import_task)
    
    return {
        "message": f"Import lancé pour {len(request.item_ids)} items",
        "status": "Import en cours en arrière-plan"
    }

@router.get("/stats")
async def get_drop_stats(db: Session = Depends(get_db)):
    """Récupère les statistiques des données de drop en cache"""
    total_drops = db.query(MonsterDrop).count()
    total_monsters = db.query(CachedMonster).count()
    
    # Items uniques avec des drops
    unique_items = db.query(MonsterDrop.item_id).distinct().count()
    
    # Top 5 monstres avec le plus de drops
    from sqlalchemy import func
    top_monsters = db.query(
        MonsterDrop.monster_name,
        func.count(MonsterDrop.item_id).label('drop_count')
    ).group_by(MonsterDrop.monster_name).order_by(
        func.count(MonsterDrop.item_id).desc()
    ).limit(5).all()
    
    return {
        "total_drops": total_drops,
        "total_monsters": total_monsters,
        "unique_items_with_drops": unique_items,
        "top_monsters": [
            {"name": m[0], "drop_count": m[1]} for m in top_monsters
        ]
    }

class JSONFileImportRequest(BaseModel):
    """Format pour l'import de fichiers JSON de scraping"""
    monsters: List[dict]  # Liste directe des monstres au format JSON

@router.post("/import-json")
async def import_json_file(request: JSONFileImportRequest, db: Session = Depends(get_db)):
    """
    Importe des données depuis un fichier JSON au format de scraping
    
    Format attendu (supporte les deux formats de drop rate):
    {
        "monsters": [
            {
                "id": "5314",
                "name": "Capt'chat",
                "url": "https://www.wakfu.com/fr/mmorpg/encyclopedie/monstres/5314-capt-chat",
                "drops": [
                    {
                        "item_id": "123",
                        "item_name": "Item Name", 
                        "drop_rate": 25.5      // Format 1: float
                    },
                    {
                        "item_id": "456",
                        "item_name": "Autre Item",
                        "drop_perc": "15%"      // Format 2: string avec %
                    }
                ]
            }
        ]
    }
    """
    from sqlalchemy import and_
    
    results = {
        'monsters_processed': 0,
        'monsters_added': 0,
        'drops_added': 0,
        'drops_updated': 0,
        'errors': []
    }
    
    try:
        # Traiter chaque monstre
        for monster_data in request.monsters:
            try:
                # Extraire les infos de base
                monster_id = monster_data.get('id')
                if isinstance(monster_id, str):
                    monster_id = int(monster_id)
                
                monster_name = monster_data.get('name', 'Unknown')
                monster_url = monster_data.get('url', '')
                
                if not monster_id:
                    results['errors'].append(f"Monstre sans ID ignoré: {monster_name}")
                    continue
                
                results['monsters_processed'] += 1
                
                # Extraire le niveau depuis l'URL ou les données si disponible
                monster_level = monster_data.get('level')
                
                # Vérifier/créer le monstre en cache
                cached_monster = db.query(CachedMonster).filter(
                    CachedMonster.wakfu_id == monster_id
                ).first()
                
                if not cached_monster:
                    cached_monster = CachedMonster(
                        wakfu_id=monster_id,
                        name=monster_name,
                        level=monster_level,
                        data_json={
                            'name': monster_name,
                            'level': monster_level,
                            'url': monster_url,
                            'imported_from_json_at': str(datetime.utcnow())
                        }
                    )
                    db.add(cached_monster)
                    results['monsters_added'] += 1
                else:
                    # Mettre à jour les infos si nécessaire
                    if cached_monster.name != monster_name:
                        cached_monster.name = monster_name
                    if monster_level and cached_monster.level != monster_level:
                        cached_monster.level = monster_level
                
                # Traiter les drops
                for drop_data in monster_data.get('drops', []):
                    try:
                        item_id = drop_data.get('item_id')
                        if isinstance(item_id, str):
                            item_id = int(item_id)
                        
                        # Gérer les deux formats: drop_rate (float) ou drop_perc (string avec %)
                        drop_rate = drop_data.get('drop_rate')
                        if drop_rate is None:
                            drop_perc = drop_data.get('drop_perc')
                            if drop_perc:
                                # Convertir "25%" -> 25.0
                                drop_rate = float(drop_perc.replace('%', '').strip())
                        
                        if isinstance(drop_rate, str):
                            drop_rate = float(drop_rate)
                        
                        item_name = drop_data.get('item_name', '')
                        
                        if not item_id or drop_rate is None:
                            continue
                        
                        # Vérifier si le drop existe déjà
                        existing_drop = db.query(MonsterDrop).filter(
                            and_(
                                MonsterDrop.monster_id == monster_id,
                                MonsterDrop.item_id == item_id
                            )
                        ).first()
                        
                        if existing_drop:
                            # Mettre à jour si différent
                            if abs(existing_drop.drop_rate - drop_rate) > 0.01:  # Tolérance pour les flottants
                                existing_drop.drop_rate = drop_rate
                                results['drops_updated'] += 1
                        else:
                            # Créer nouveau drop
                            new_drop = MonsterDrop(
                                monster_id=monster_id,
                                monster_name=monster_name,
                                monster_level=monster_level,
                                item_id=item_id,
                                drop_rate=drop_rate
                            )
                            db.add(new_drop)
                            results['drops_added'] += 1
                    
                    except (ValueError, TypeError) as e:
                        results['errors'].append(f"Drop invalide pour {monster_name}: {str(e)}")
                        continue
                
                # Commit après chaque monstre pour éviter de perdre tout en cas d'erreur
                db.commit()
                
            except (ValueError, TypeError) as e:
                db.rollback()
                results['errors'].append(f"Erreur monstre {monster_data.get('name', 'Unknown')}: {str(e)}")
                continue
            except Exception as e:
                db.rollback()
                results['errors'].append(f"Erreur inattendue monstre {monster_data.get('name', 'Unknown')}: {str(e)}")
                continue
        
        # Résultat final
        success_rate = (results['monsters_processed'] - len(results['errors'])) / max(results['monsters_processed'], 1) * 100
        
        return {
            "message": f"Import JSON terminé avec {success_rate:.1f}% de succès",
            "results": results,
            "summary": {
                "total_monsters": results['monsters_processed'],
                "successful": results['monsters_processed'] - len(results['errors']),
                "failed": len(results['errors']),
                "new_monsters": results['monsters_added'],
                "new_drops": results['drops_added'],
                "updated_drops": results['drops_updated']
            }
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erreur lors de l'import JSON: {str(e)}")

@router.delete("/clear")
async def clear_drop_data(db: Session = Depends(get_db)):
    """
    ⚠️ DANGER: Supprime toutes les données de drop de la base
    """
    try:
        # Supprimer tous les drops
        db.query(MonsterDrop).delete()
        # Supprimer tous les monstres cachés
        db.query(CachedMonster).delete()
        db.commit()
        
        return {"message": "Toutes les données de drop ont été supprimées"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))