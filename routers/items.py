from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel

from core.database import get_db
from models.cache import CachedItem

router = APIRouter(prefix="/items", tags=["items"])

class ItemResponse(BaseModel):
    id: int
    wakfu_id: int
    data_json: dict
    obtention_type: Optional[str]
    last_updated: str
    
    class Config:
        from_attributes = True

@router.get("/{item_id}", response_model=ItemResponse)
async def get_item(item_id: int, db: Session = Depends(get_db)):
    """Récupère les détails d'un item"""
    item = db.query(CachedItem).filter(
        CachedItem.wakfu_id == item_id
    ).first()
    
    if not item:
        raise HTTPException(status_code=404, detail="Item non trouvé")
    
    return item

@router.get("/{item_id}/obtention")
async def get_item_obtention(item_id: int, db: Session = Depends(get_db)):
    """Récupère les infos d'obtention d'un item"""
    item = db.query(CachedItem).filter(
        CachedItem.wakfu_id == item_id
    ).first()
    
    if not item:
        raise HTTPException(status_code=404, detail="Item non trouvé")
    
    # Infos basiques d'obtention
    obtention_info = {
        "item_id": item_id,
        "obtention_type": item.obtention_type,
        "details": {}
    }
    
    if item.obtention_type == "craft":
        obtention_info["details"] = {
            "message": "Cet item se craft",
            "action": "Chercher la recette dans les métiers"
        }
    elif item.obtention_type == "harvest":
        obtention_info["details"] = {
            "message": "Cet item se récolte",
            "action": "Chercher les zones de récolte"
        }
    elif item.obtention_type == "shop":
        obtention_info["details"] = {
            "message": "Cet item s'achète en boutique",
            "action": "Disponible uniquement en boutique"
        }
    else:
        obtention_info["details"] = {
            "message": "Mode d'obtention inconnu",
            "action": "Vérifier en jeu"
        }
    
    return obtention_info