from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from core.database import SessionLocal
from models.cache import CachedItem, FarmAnalysis
from services.wakfu_cdn import wakfu_cdn

class AnalysisService:
    def __init__(self):
        pass
    
    async def update_items_cache(self, items: List[Dict], recipes: List[Dict], harvest_loots: List[Dict]):
        """Met à jour le cache des items avec analyse d'obtention"""
        db = SessionLocal()
        try:
            print(f"Analyse de {len(items)} items...")
            
            for item in items:
                item_data = item.get("definition", {}).get("item", {})
                item_id = item_data.get("id")
                
                if not item_id:
                    continue
                
                # Analyse du type d'obtention
                obtention_type = wakfu_cdn.analyze_item_obtention(item, recipes, harvest_loots)
                
                # Vérifier si l'item existe déjà
                existing_item = db.query(CachedItem).filter(
                    CachedItem.wakfu_id == item_id
                ).first()
                
                if existing_item:
                    # Mettre à jour
                    existing_item.data_json = item
                    existing_item.obtention_type = obtention_type
                else:
                    # Créer nouveau
                    new_item = CachedItem(
                        wakfu_id=item_id,
                        data_json=item,
                        obtention_type=obtention_type
                    )
                    db.add(new_item)
            
            db.commit()
            print("Cache des items mis à jour")
            
        except Exception as e:
            db.rollback()
            print(f"Erreur mise à jour cache: {e}")
        finally:
            db.close()
    
    async def analyze_build_for_farming(self, build_id: int, items_ids: List[int]) -> Dict:
        """Analyse un build pour générer la roadmap de farm"""
        db = SessionLocal()
        try:
            analysis_results = {
                "build_id": build_id,
                "total_items": len(items_ids),
                "farm_breakdown": {
                    "craft": [],
                    "harvest": [],
                    "shop": [],
                    "treasure": [],
                    "unknown": []
                }
            }
            
            for item_id in items_ids:
                # Récupère l'item du cache
                cached_item = db.query(CachedItem).filter(
                    CachedItem.wakfu_id == item_id
                ).first()
                
                if not cached_item:
                    continue
                
                # Créer ou mettre à jour l'analyse de farm
                existing_analysis = db.query(FarmAnalysis).filter(
                    FarmAnalysis.build_id == build_id,
                    FarmAnalysis.item_id == item_id
                ).first()
                
                farm_data = self._generate_farm_data(cached_item)
                
                if existing_analysis:
                    existing_analysis.obtention_type = cached_item.obtention_type
                    existing_analysis.farm_data = farm_data
                else:
                    new_analysis = FarmAnalysis(
                        build_id=build_id,
                        item_id=item_id,
                        obtention_type=cached_item.obtention_type,
                        farm_data=farm_data
                    )
                    db.add(new_analysis)
                
                # Ajouter à la breakdown
                obtention_type = cached_item.obtention_type or "unknown"
                analysis_results["farm_breakdown"][obtention_type].append({
                    "item_id": item_id,
                    "item_name": cached_item.data_json.get("title", {}).get("fr", f"Item {item_id}"),
                    "farm_data": farm_data
                })
            
            db.commit()
            return analysis_results
            
        except Exception as e:
            db.rollback()
            print(f"Erreur analyse build: {e}")
            return {"error": str(e)}
        finally:
            db.close()
    
    def _generate_farm_data(self, cached_item: CachedItem) -> Dict:
        """Génère les données de farm spécifiques selon le type d'obtention"""
        obtention_type = cached_item.obtention_type
        item_data = cached_item.data_json
        
        if obtention_type == "craft":
            return {
                "type": "craft",
                "message": "Item craftable",
                "action": "Chercher la recette et les ingrédients",
                "priority": "medium"
            }
        
        elif obtention_type == "harvest":
            return {
                "type": "harvest", 
                "message": "Item récoltable",
                "action": "Aller dans les zones de récolte appropriées",
                "priority": "high"
            }
        
        elif obtention_type == "shop":
            return {
                "type": "shop",
                "message": "Item boutique uniquement",
                "action": "Acheter en boutique",
                "priority": "low"
            }
        
        elif obtention_type == "treasure":
            return {
                "type": "treasure",
                "message": "Item trésor spécial",
                "action": "Obtenir via quêtes ou événements spéciaux",
                "priority": "high"
            }
        
        else:
            return {
                "type": "unknown",
                "message": "Mode d'obtention inconnu",
                "action": "Vérifier en jeu ou sur les wikis",
                "priority": "unknown"
            }

analysis_service = AnalysisService()