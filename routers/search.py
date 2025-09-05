from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import List, Optional
from pydantic import BaseModel
import json
import re

from core.database import get_db
from models.cache import CachedItem

router = APIRouter(prefix="/search", tags=["search"])

class ItemSearchResult(BaseModel):
    wakfu_id: int
    name: str
    level: Optional[int] = None
    item_type: Optional[str] = None
    rarity: Optional[str] = None
    match_score: float
    obtention_type: Optional[str] = None

class ItemSearchRequest(BaseModel):
    query: str
    limit: Optional[int] = 20

class BuildFromTextRequest(BaseModel):
    items_text: str  # "Épée Iop, Cape du Feu, Anneau PA"
    build_name: Optional[str] = None

@router.post("/items", response_model=List[ItemSearchResult])
async def search_items(request: ItemSearchRequest, db: Session = Depends(get_db)):
    """
    Recherche d'items par nom/texte avec scoring de pertinence
    """
    query = request.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query ne peut pas être vide")
    
    # Récupérer tous les items depuis le cache
    cached_items = db.query(CachedItem).all()
    
    if not cached_items:
        raise HTTPException(status_code=404, detail="Aucun item trouvé en cache. Synchronisez le CDN d'abord.")
    
    results = []
    query_lower = query.lower()
    
    for cached_item in cached_items:
        try:
            # Extraire le nom depuis les données JSON
            item_data = cached_item.data_json
            if not isinstance(item_data, dict):
                continue
            
            item_name = item_data.get('title', {}).get('fr', '')
            if not item_name:
                continue
            
            # Calculer le score de correspondance
            score = calculate_match_score(query_lower, item_name.lower())
            
            if score > 0:  # Seulement si il y a une correspondance
                # Extraire les infos supplémentaires
                level = item_data.get('level')
                item_type = get_item_type(item_data)
                rarity = get_item_rarity(item_data)
                
                results.append(ItemSearchResult(
                    wakfu_id=cached_item.wakfu_id,
                    name=item_name,
                    level=level,
                    item_type=item_type,
                    rarity=rarity,
                    match_score=score,
                    obtention_type=cached_item.obtention_type
                ))
        
        except Exception as e:
            continue  # Ignorer les items avec des données malformées
    
    # Trier par score décroissant
    results.sort(key=lambda x: x.match_score, reverse=True)
    
    return results[:request.limit]

@router.post("/build-from-text")
async def create_build_from_text(request: BuildFromTextRequest, db: Session = Depends(get_db)):
    """
    Crée un build à partir d'une liste d'items en texte
    Exemple: "Épée Iop, Cape du Feu, Anneau PA"
    """
    if not request.items_text.strip():
        raise HTTPException(status_code=400, detail="Liste d'items ne peut pas être vide")
    
    # Séparer les items (par virgule, point-virgule ou retour à la ligne)
    item_names = re.split(r'[,;\n]', request.items_text)
    item_names = [name.strip() for name in item_names if name.strip()]
    
    if not item_names:
        raise HTTPException(status_code=400, detail="Aucun nom d'item valide trouvé")
    
    # Rechercher chaque item
    found_items = []
    missing_items = []
    
    for item_name in item_names:
        # Chercher le meilleur match pour cet item
        search_result = await search_items(
            ItemSearchRequest(query=item_name, limit=1), 
            db
        )
        
        if search_result and search_result[0].match_score >= 0.3:  # Score minimum
            found_items.append({
                'input_name': item_name,
                'found_item': search_result[0],
                'wakfu_id': search_result[0].wakfu_id
            })
        else:
            missing_items.append(item_name)
    
    if not found_items:
        raise HTTPException(
            status_code=404, 
            detail=f"Aucun item trouvé pour: {', '.join(missing_items)}"
        )
    
    # Créer le build avec les items trouvés
    items_ids = [item['wakfu_id'] for item in found_items]
    
    # Utiliser le drop_manager pour générer la roadmap
    from services.drop_manager import drop_manager
    roadmap = drop_manager.get_farm_roadmap(items_ids)
    
    return {
        'build_name': request.build_name or f"Build depuis texte ({len(found_items)} items)",
        'items_found': found_items,
        'items_missing': missing_items,
        'items_count': len(found_items),
        'missing_count': len(missing_items),
        'farm_roadmap': roadmap
    }

def calculate_match_score(query: str, item_name: str) -> float:
    """
    Calcule un score de correspondance entre 0 et 1
    """
    if not query or not item_name:
        return 0.0
    
    query = query.lower().strip()
    item_name = item_name.lower().strip()
    
    # Score parfait si correspondance exacte
    if query == item_name:
        return 1.0
    
    # Score élevé si l'item contient la query complète
    if query in item_name:
        return 0.9 - (len(item_name) - len(query)) / len(item_name) * 0.3
    
    # Score pour correspondance partielle (mots individuels)
    query_words = query.split()
    item_words = item_name.split()
    
    matches = 0
    for query_word in query_words:
        for item_word in item_words:
            if query_word in item_word or item_word in query_word:
                matches += 1
                break
    
    if matches == 0:
        return 0.0
    
    # Score basé sur le pourcentage de mots correspondants
    word_score = matches / max(len(query_words), len(item_words))
    
    # Bonus si le début correspond
    if item_name.startswith(query):
        word_score += 0.3
    
    return min(word_score, 1.0)

def get_item_type(item_data: dict) -> Optional[str]:
    """Extrait le type d'item depuis les données CDN"""
    try:
        # Essayer différents champs possibles
        if 'definition' in item_data:
            def_data = item_data['definition']
            if 'item' in def_data:
                item_info = def_data['item']
                return item_info.get('itemType', item_info.get('category'))
        
        # Autres possibilités
        return item_data.get('itemType') or item_data.get('category')
    except:
        return None

def get_item_rarity(item_data: dict) -> Optional[str]:
    """Extrait la rareté depuis les données CDN"""
    try:
        rarity_id = item_data.get('definition', {}).get('item', {}).get('rarity')
        if rarity_id is not None:
            rarity_map = {
                0: "Commun",
                1: "Rare", 
                2: "Mythique",
                3: "Légendaire",
                4: "Relique",
                5: "Épique"
            }
            return rarity_map.get(rarity_id, f"Rareté {rarity_id}")
        return None
    except:
        return None