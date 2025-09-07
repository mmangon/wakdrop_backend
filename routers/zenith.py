"""
Router pour l'import de builds depuis ZenithWakfu
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from pydantic import BaseModel, HttpUrl
from typing import Dict, List, Optional
import asyncio
import json
import re
import os
from pathlib import Path

from core.database import get_db
from models.build import Build
from models.cache import CachedItem, MonsterDrop
from models.zones import Zone, MonsterZone

# Subprocess pour extraction
import subprocess
import json as json_lib
import sys

router = APIRouter(prefix="/zenith", tags=["zenith"])

class ZenithImportRequest(BaseModel):
    zenith_url: str
    build_name: Optional[str] = None

class ZenithImportResponse(BaseModel):
    build_id: int
    build_name: str
    items_found: List[Dict]
    items_missing: List[str]
    farm_roadmap: Optional[Dict] = None
    message: str

def extract_item_id_from_html(html: str) -> Optional[int]:
    """
    Extrait l'ID Wakfu depuis le HTML de la tooltip
    L'ID est dans l'attribut alt de l'image: alt="items/ID"
    """
    if not html:
        return None
    
    # Chercher le pattern alt="items/ID"
    match = re.search(r'alt="items/(\d+)"', html)
    if match:
        return int(match.group(1))
    
    # Pattern alternatif src="../images/items/ID.webp"
    match = re.search(r'src="[^"]*items/(\d+)\.(webp|png|jpg)"', html)
    if match:
        return int(match.group(1))
    
    return None

@router.post("/import")
async def import_from_zenith(
    request: ZenithImportRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Importe un build depuis ZenithWakfu
    
    1. Extrait les items depuis l'URL Zenith
    2. Mappe avec les items en cache
    3. Crée un build
    4. Génère la roadmap de farm
    """
    
    # Valider l'URL Zenith
    if "zenithwakfu.com/builder/" not in request.zenith_url:
        raise HTTPException(status_code=400, detail="URL invalide. Doit être une URL ZenithWakfu.")
    
    # Extraire l'ID du build depuis l'URL
    zenith_build_id = request.zenith_url.split("/builder/")[-1].split("?")[0].split("#")[0]
    
    # Nom du build par défaut
    build_name = request.build_name or f"Build Zenith {zenith_build_id}"
    
    try:
        # Extraire les noms d'items depuis Zenith via subprocess
        script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "services", "zenith", "extract_zenith_names_subprocess.py"))
        venv_python = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "venv", "bin", "python"))
        
        result = subprocess.run(
            [venv_python, script_path, request.zenith_url],
            capture_output=True,
            text=True,
            timeout=90,  # 90 seconds max
            cwd=os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))  # Set working directory
        )
        
        if result.returncode != 0:
            print(f"SUBPROCESS ERROR - Return code: {result.returncode}")
            print(f"SUBPROCESS ERROR - Stderr: {result.stderr}")
            print(f"SUBPROCESS ERROR - Stdout: {result.stdout}")
            raise HTTPException(status_code=500, detail=f"Erreur extraction (code {result.returncode}): {result.stderr}")
        
        try:
            extraction_result = json_lib.loads(result.stdout)
        except json_lib.JSONDecodeError as json_err:
            raise HTTPException(status_code=500, detail=f"Erreur parsing JSON: {json_err} - Stdout: {result.stdout}")
        
        if not extraction_result.get("success"):
            raise HTTPException(status_code=500, detail=f"Erreur: {extraction_result.get('error')}")
        
        # Récupérer les résultats de l'extraction par noms
        extraction_method = extraction_result.get("extraction_method", "names")
        zenith_items_count = extraction_result.get("zenith_items_found", 0)
        cache_matches_count = extraction_result.get("cache_matches", 0)
        
        if zenith_items_count == 0:
            raise HTTPException(status_code=404, detail="Aucun item trouvé dans ce build Zenith")
        
        # Récupérer les items matchés
        items_details = extraction_result.get("items_details", [])
        items_missing = extraction_result.get("items_missing", [])
        valid_item_ids = extraction_result.get("item_ids", [])
        
        
        # Mapping des raretés ZenithWakfu vers français
        zenith_rarity_mapping = {
            'legendary': 'Légendaire',
            'mythic': 'Mythique', 
            'epic': 'Épique',
            'relic': 'Relique',
            'rare': 'Rare',
            'unusual': 'Inhabituel',
            'uncommon': 'Inhabituel',
            'common': 'Commun'
        }
        
        # Préparer les items trouvés dans le même format que /builds/{id}
        items_found = []
        for item_detail in items_details:
            wakfu_id = item_detail.get('wakfu_id')
            zenith_name = item_detail.get('zenith_name', '')
            
            # Récupérer les détails complets depuis le cache
            cached_item = db.query(CachedItem).filter(
                CachedItem.wakfu_id == wakfu_id
            ).first()
            
            if cached_item:
                try:
                    item_data = cached_item.data_json
                    item_name = item_data.get('title', {}).get('fr', f'Item {wakfu_id}') if isinstance(item_data, dict) else f'Item {wakfu_id}'
                    
                    # Extraire les infos supplémentaires (EXACTEMENT comme builds.py)
                    from routers.search import get_item_type
                    level = item_data.get('definition', {}).get('item', {}).get('level') if isinstance(item_data, dict) else None
                    item_type = get_item_type(item_data) if isinstance(item_data, dict) else None
                    
                    # SOLUTION FINALE : Mapping correct des raretés ZenithWakfu
                    zenith_rarity = item_detail.get('zenith_rarity', 'unknown')
                    
                    # Mapping ZenithWakfu -> Français
                    if zenith_rarity == 'legendary':
                        rarity = 'Légendaire'
                    elif zenith_rarity == 'mythic':
                        rarity = 'Mythique'
                    elif zenith_rarity == 'epic':
                        rarity = 'Épique'
                    elif zenith_rarity == 'relic':
                        rarity = 'Relique'
                    elif zenith_rarity == 'rare':
                        rarity = 'Rare'
                    elif zenith_rarity == 'unusual' or zenith_rarity == 'uncommon':
                        rarity = 'Inhabituel'
                    elif zenith_rarity == 'common':
                        rarity = 'Commun'
                    else:
                        # Fallback au CDN seulement si vraiment inconnu
                        from routers.search import get_item_rarity
                        rarity = get_item_rarity(item_data) if isinstance(item_data, dict) else 'Inconnu'
                    
                    # Structure PLATE attendue par le frontend
                    items_found.append({
                        'wakfu_id': wakfu_id,
                        'name': item_name,
                        'level': level,
                        'item_type': item_type,
                        'rarity': rarity,
                        'match_score': 1.0,  # Score parfait comme dans builds.py
                        'obtention_type': cached_item.obtention_type
                    })
                except Exception as e:
                    items_missing.append(f'Item {wakfu_id} (erreur de données)')
            else:
                items_missing.append(f'Item {wakfu_id} (non trouvé en cache)')
        
        item_ids = valid_item_ids
        
        if not item_ids:
            # Si aucun item n'est trouvé, retourner une réponse informative au lieu d'une erreur
            return ZenithImportResponse(
                build_id=0,  # Pas de build créé
                build_name=build_name,
                items_found=[],
                items_missing=items_missing,
                farm_roadmap=None,
                message=f"Build Zenith analysé : {zenith_items_count} items détectés, mais aucun match trouvé dans notre base de données. "
                        f"Cela peut arriver si les noms d'items sont trop différents ou si les items sont introuvables."
            )
        
        # Créer le build dans la base
        db_build = Build(
            build_name=build_name,
            items_ids=item_ids
        )
        db.add(db_build)
        db.commit()
        db.refresh(db_build)
        
        # Générer la roadmap avec le drop_manager (EXACTEMENT comme builds.py)
        from services.drop_manager import drop_manager
        roadmap = drop_manager.get_farm_roadmap(item_ids)
        
        # Retourner la même structure que /builds/{id}
        return {
            'build_id': db_build.id,
            'build_name': db_build.build_name,
            'items_found': items_found,
            'items_missing': items_missing,
            'items_count': len(items_found),
            'missing_count': len(items_missing),
            'farm_roadmap': roadmap,
            'created_at': db_build.created_at
        }
        
    except Exception as e:
        import traceback
        error_msg = str(e) or "Erreur inconnue"
        tb = traceback.format_exc()
        print(f"ERROR in zenith import: {error_msg}")
        print(f"Full traceback: {tb}")
        raise HTTPException(status_code=500, detail=f"Erreur lors de l'import: {error_msg}")



@router.get("/import/{build_id}")
async def get_imported_build(build_id: int, db: Session = Depends(get_db)):
    """
    Récupère un build importé depuis Zenith avec sa roadmap complète
    Même format que /builds/{id}
    """
    # Utiliser le même code que builds.py
    from routers.builds import get_build
    return await get_build(build_id, db)