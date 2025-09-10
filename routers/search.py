from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import List, Optional
from pydantic import BaseModel, Field
import json
import re

from core.database import get_db
from models.cache import CachedItem, MonsterDrop, CachedMonster
from models.zones import MonsterZone, Zone

router = APIRouter(prefix="/search", tags=["search"])

class MonsterInfo(BaseModel):
    id: int
    name: str
    level: Optional[int] = None
    zone: Optional[str] = None
    drop_rate: float = Field(alias="dropRate")
    
    class Config:
        populate_by_name = True

class ItemSearchResult(BaseModel):
    wakfu_id: int
    name: str
    level: Optional[int] = None
    item_type: Optional[str] = None
    rarity: Optional[str] = None
    match_score: float
    obtention_type: Optional[str] = None
    monsters: List[MonsterInfo] = []

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
            
            # Gestion des 2 formats: CDN (title.fr) et bestiaire (title direct)
            title_data = item_data.get('title', '')
            if isinstance(title_data, dict):
                # Format CDN: title.fr
                item_name = title_data.get('fr', '')
            elif isinstance(title_data, str):
                # Format bestiaire: title direct
                item_name = title_data
            else:
                item_name = ''
            
            if not item_name:
                continue
            
            # Calculer le score de correspondance
            score = calculate_match_score(query_lower, item_name.lower())
            
            if score > 0:  # Seulement si il y a une correspondance
                # Extraire les infos supplémentaires
                level = item_data.get('definition', {}).get('item', {}).get('level')
                item_type = get_item_type(item_data)
                rarity = get_item_rarity(item_data)
                
                # Récupérer les données de drop
                monsters_info = get_item_monsters(cached_item.wakfu_id, db)
                
                results.append(ItemSearchResult(
                    wakfu_id=cached_item.wakfu_id,
                    name=item_name,
                    level=level,
                    item_type=item_type,
                    rarity=rarity,
                    match_score=score,
                    obtention_type=cached_item.obtention_type,
                    monsters=monsters_info
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
        # Chercher les meilleurs matchs pour cet item (plus large pour évaluer les raretés)
        search_results = await search_items(
            ItemSearchRequest(query=item_name, limit=10), 
            db
        )
        
        if search_results:
            # Sélectionner le meilleur résultat en tenant compte de la rareté
            best_item = select_best_item_with_rarity(item_name, search_results)
            
            if best_item and best_item.match_score >= 0.3:  # Score minimum
                # Structure PLATE attendue par le frontend
                found_items.append({
                    'wakfu_id': best_item.wakfu_id,
                    'name': best_item.name,
                    'level': best_item.level,
                    'item_type': best_item.item_type,
                    'rarity': best_item.rarity,
                    'match_score': best_item.match_score,
                    'obtention_type': best_item.obtention_type
                })
            else:
                missing_items.append(item_name)
        else:
            missing_items.append(item_name)
    
    if not found_items:
        raise HTTPException(
            status_code=404, 
            detail=f"Aucun item trouvé pour: {', '.join(missing_items)}"
        )
    
    # Créer le build avec les items trouvés (structure plate)
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
    
    # Normaliser les textes pour la comparaison (enlever apostrophes, accents, etc.)
    def normalize_text(text):
        # Remplacer les apostrophes et caractères spéciaux
        text = text.replace("'", " ").replace("'", " ").replace("-", " ")
        # Remplacer les accents
        text = text.replace("à", "a").replace("é", "e").replace("è", "e").replace("ê", "e")
        text = text.replace("î", "i").replace("ô", "o").replace("ù", "u").replace("û", "u")
        text = text.replace("ç", "c").replace("â", "a").replace("ï", "i")
        # Enlever les espaces multiples
        return " ".join(text.split())
    
    query_norm = normalize_text(query)
    item_norm = normalize_text(item_name)
    
    # Score parfait si correspondance exacte (normalisée)
    if query_norm == item_norm:
        return 1.0
    
    # Score parfait si correspondance exacte (originale)
    if query == item_name:
        return 1.0
    
    # Score élevé si l'item contient la query complète (normalisée)
    if query_norm in item_norm:
        return 0.9 - (len(item_norm) - len(query_norm)) / len(item_norm) * 0.3
    
    # Score élevé si l'item contient la query complète (originale)
    if query in item_name:
        return 0.9 - (len(item_name) - len(query)) / len(item_name) * 0.3
    
    # Score pour correspondance partielle (mots individuels) - utiliser textes normalisés
    query_words = query_norm.split()
    item_words = item_norm.split()
    
    # Vérifier si tous les mots de la query correspondent exactement
    exact_word_matches = 0
    for query_word in query_words:
        if query_word in item_words:
            exact_word_matches += 1
    
    # Si tous les mots correspondent exactement, score très élevé
    if exact_word_matches == len(query_words):
        return 0.95
    
    # Sinon, chercher des correspondances partielles (mais pas pour les mots trop courts)
    matches = 0
    for query_word in query_words:
        matched = False
        for item_word in item_words:
            # Ignorer les mots très courts (1-2 caractères) pour les correspondances partielles
            if len(query_word) <= 2 and len(item_word) <= 2:
                if query_word == item_word:
                    matched = True
                    break
            else:
                # Pour les mots plus longs, autoriser les correspondances partielles
                if len(query_word) > 2 and query_word in item_word:
                    matched = True
                    break
                elif len(item_word) > 2 and item_word in query_word:
                    matched = True
                    break
        if matched:
            matches += 1
    
    if matches == 0:
        return 0.0
    
    # Score basé sur le pourcentage de mots correspondants
    word_score = matches / len(query_words) * 0.7  # Réduire le score de base
    
    # Bonus si le début correspond
    if item_name.startswith(query):
        word_score += 0.3
    
    return min(word_score, 1.0)

def select_best_item_with_rarity(query: str, search_results: List[ItemSearchResult]) -> Optional[ItemSearchResult]:
    """
    Sélectionne le meilleur item en tenant compte de la rareté mentionnée dans la query
    """
    if not search_results:
        return None
    
    query_lower = query.lower()
    
    # Mots-clés de rareté
    rarity_keywords = {
        'commun': 'Commun',
        'inhabituel': 'Inhabituel', 
        'rare': 'Rare',
        'mythique': 'Mythique',
        'légendaire': 'Légendaire',
        'legendaire': 'Légendaire',
        'relique': 'Relique',
        'épique': 'Épique',
        'epique': 'Épique'
    }
    
    # Chercher si une rareté est mentionnée dans la query
    mentioned_rarity = None
    for keyword, rarity in rarity_keywords.items():
        if keyword in query_lower:
            mentioned_rarity = rarity
            break
    
    # Si une rareté est mentionnée, privilégier les items de cette rareté
    if mentioned_rarity:
        for result in search_results:
            if result.rarity == mentioned_rarity:
                # Ajuster le score pour privilégier la correspondance exacte de rareté
                result.match_score = min(result.match_score + 0.2, 1.0)
                return result
    
    # Sinon, retourner le premier résultat (meilleur score)
    return search_results[0]

def get_item_type(item_data: dict) -> Optional[str]:
    """Extrait le type d'item depuis les données CDN"""
    try:
        # Essayer de récupérer itemTypeId depuis baseParameters
        if 'definition' in item_data:
            def_data = item_data['definition']
            if 'item' in def_data:
                item_info = def_data['item']
                # Chercher dans baseParameters
                base_params = item_info.get('baseParameters', {})
                item_type_id = base_params.get('itemTypeId')
                if item_type_id:
                    # Mapper les IDs de type aux noms (à compléter)
                    type_map = {
                        134: "Coiffe",
                        133: "Casque",
                        136: "Cape",
                        138: "Plastron",
                        119: "Anneau",
                        120: "Amulette",
                        103: "Bottes",
                        132: "Ceinture",
                        646: "Épaulettes"
                    }
                    return type_map.get(item_type_id, f"Type {item_type_id}")
        
        # Autres possibilités
        return item_data.get('itemType') or item_data.get('category')
    except:
        return None

def get_item_rarity(item_data: dict) -> Optional[str]:
    """Extrait la rareté depuis les données CDN"""
    try:
        # Chercher dans baseParameters
        base_params = item_data.get('definition', {}).get('item', {}).get('baseParameters', {})
        rarity_id = base_params.get('rarity')
        if rarity_id is not None:
            rarity_map = {
                0: "Commun",
                1: "Inhabituel",
                2: "Rare",
                3: "Mythique",
                4: "Légendaire",
                5: "Relique",
                6: "Souvenir",
                7: "Épique"
            }
            return rarity_map.get(rarity_id, f"Rareté {rarity_id}")
        return None
    except:
        return None

def get_item_monsters(item_id: int, db: Session) -> List[MonsterInfo]:
    """Récupère les monstres qui drop un item donné"""
    try:
        # Joindre MonsterDrop, CachedMonster et MonsterZone pour récupérer toutes les infos
        query = (
            db.query(MonsterDrop, CachedMonster, Zone)
            .join(CachedMonster, MonsterDrop.monster_id == CachedMonster.wakfu_id)
            .outerjoin(MonsterZone, MonsterZone.monster_id == CachedMonster.wakfu_id)
            .outerjoin(Zone, MonsterZone.zone_id == Zone.id)
            .filter(MonsterDrop.item_id == item_id)
            .filter(MonsterDrop.drop_rate > 0)  # Seulement les drops avec taux > 0
            .order_by(MonsterDrop.drop_rate.desc())  # Trier par taux décroissant
        )
        
        results = query.all()
        
        monsters = []
        for drop, monster, zone in results:
            monsters.append(MonsterInfo(
                id=monster.wakfu_id,
                name=monster.name,
                level=monster.level,
                zone=zone.name if zone else None,
                dropRate=drop.drop_rate
            ))
        
        return monsters
        
    except Exception as e:
        # En cas d'erreur avec la jointure, faire une requête simple sur monster_drops
        try:
            simple_query = (
                db.query(MonsterDrop)
                .filter(MonsterDrop.item_id == item_id)
                .filter(MonsterDrop.drop_rate > 0)
                .order_by(MonsterDrop.drop_rate.desc())
            )
            
            results = simple_query.all()
            monsters = []
            for drop in results:
                monsters.append(MonsterInfo(
                    id=drop.monster_id,
                    name=drop.monster_name,
                    level=drop.monster_level,
                    zone=drop.zone_name,
                    dropRate=drop.drop_rate
                ))
            
            return monsters
        except:
            return []