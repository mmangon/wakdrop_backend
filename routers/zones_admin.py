from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional
from pydantic import BaseModel

from core.database import get_db
from models.zones import Zone, MonsterZone

router = APIRouter(prefix="/admin/zones", tags=["zones-admin"])

# Pydantic Models
class ZoneCreate(BaseModel):
    name: str
    description: Optional[str] = None
    min_level: Optional[int] = None
    max_level: Optional[int] = None

class ZoneResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    min_level: Optional[int]
    max_level: Optional[int]
    monster_count: Optional[int] = 0

class MonsterInfo(BaseModel):
    monster_id: int
    monster_name: Optional[str]
    spawn_frequency: Optional[str]
    notes: Optional[str]

class MonsterZoneCreate(BaseModel):
    monster_id: int

class ZoneDetailResponse(ZoneResponse):
    monsters: List[MonsterInfo] = []

# Endpoints pour les Zones
@router.get("/zones", response_model=List[ZoneResponse])
async def list_zones(db: Session = Depends(get_db)):
    """Liste toutes les zones avec le nombre de monstres"""
    zones = db.query(Zone).all()
    
    result = []
    for zone in zones:
        monster_count = db.query(MonsterZone).filter(MonsterZone.zone_id == zone.id).count()
        result.append(ZoneResponse(
            id=zone.id,
            name=zone.name,
            description=zone.description,
            min_level=zone.min_level,
            max_level=zone.max_level,
            monster_count=monster_count
        ))
    
    return result

@router.post("/zones", response_model=ZoneResponse)
async def create_zone(zone_data: ZoneCreate, db: Session = Depends(get_db)):
    """Crée une nouvelle zone"""
    # Vérifier si la zone existe déjà
    existing = db.query(Zone).filter(Zone.name == zone_data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Zone '{zone_data.name}' existe déjà")
    
    zone = Zone(
        name=zone_data.name,
        description=zone_data.description,
        min_level=zone_data.min_level,
        max_level=zone_data.max_level
    )
    
    db.add(zone)
    db.commit()
    db.refresh(zone)
    
    return ZoneResponse(
        id=zone.id,
        name=zone.name,
        description=zone.description,
        min_level=zone.min_level,
        max_level=zone.max_level,
        monster_count=0
    )

@router.get("/zones/{zone_id}", response_model=ZoneDetailResponse)
async def get_zone_detail(zone_id: int, db: Session = Depends(get_db)):
    """Détails d'une zone avec ses monstres"""
    zone = db.query(Zone).filter(Zone.id == zone_id).first()
    if not zone:
        raise HTTPException(status_code=404, detail="Zone introuvable")
    
    # Récupérer les monstres avec leurs noms depuis monster_drops
    monster_zones = db.query(MonsterZone).filter(MonsterZone.zone_id == zone_id).all()
    
    monsters = []
    for mz in monster_zones:
        # Récupérer le nom du monstre depuis monster_drops
        monster_name_result = db.execute(
            text("SELECT DISTINCT monster_name FROM monster_drops WHERE monster_id = :monster_id LIMIT 1"),
            {"monster_id": mz.monster_id}
        ).fetchone()
        
        monster_name = monster_name_result[0] if monster_name_result else f"Monstre {mz.monster_id}"
        
        monsters.append(MonsterInfo(
            monster_id=mz.monster_id,
            monster_name=monster_name,
            spawn_frequency=mz.spawn_frequency,
            notes=mz.notes
        ))
    
    return ZoneDetailResponse(
        id=zone.id,
        name=zone.name,
        description=zone.description,
        min_level=zone.min_level,
        max_level=zone.max_level,
        monster_count=len(monsters),
        monsters=monsters
    )

@router.delete("/zones/{zone_id}")
async def delete_zone(zone_id: int, db: Session = Depends(get_db)):
    """Supprime une zone et toutes ses associations"""
    zone = db.query(Zone).filter(Zone.id == zone_id).first()
    if not zone:
        raise HTTPException(status_code=404, detail="Zone introuvable")
    
    db.delete(zone)
    db.commit()
    
    return {"message": f"Zone '{zone.name}' supprimée"}

# Endpoints pour associer des monstres aux zones
@router.post("/zones/{zone_id}/monsters")
async def add_monster_to_zone(
    zone_id: int, 
    monster_data: MonsterZoneCreate, 
    db: Session = Depends(get_db)
):
    """Ajoute un monstre à une zone"""
    # Vérifier que la zone existe
    zone = db.query(Zone).filter(Zone.id == zone_id).first()
    if not zone:
        raise HTTPException(status_code=404, detail="Zone introuvable")
    
    # Vérifier que le monstre existe dans monster_drops
    monster_exists = db.execute(
        text("SELECT COUNT(*) FROM monster_drops WHERE monster_id = :monster_id"),
        {"monster_id": monster_data.monster_id}
    ).scalar()
    
    if monster_exists == 0:
        raise HTTPException(status_code=404, detail=f"Monstre ID {monster_data.monster_id} introuvable")
    
    # Vérifier si l'association existe déjà
    existing = db.query(MonsterZone).filter(
        MonsterZone.zone_id == zone_id,
        MonsterZone.monster_id == monster_data.monster_id
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Monstre déjà associé à cette zone")
    
    # Créer l'association
    monster_zone = MonsterZone(
        zone_id=zone_id,
        monster_id=monster_data.monster_id,
        spawn_frequency=None,
        notes=None
    )
    
    db.add(monster_zone)
    db.commit()
    
    return {"message": "Monstre ajouté à la zone"}

@router.delete("/zones/{zone_id}/monsters/{monster_id}")
async def remove_monster_from_zone(zone_id: int, monster_id: int, db: Session = Depends(get_db)):
    """Retire un monstre d'une zone"""
    monster_zone = db.query(MonsterZone).filter(
        MonsterZone.zone_id == zone_id,
        MonsterZone.monster_id == monster_id
    ).first()
    
    if not monster_zone:
        raise HTTPException(status_code=404, detail="Association monstre/zone introuvable")
    
    db.delete(monster_zone)
    db.commit()
    
    return {"message": "Monstre retiré de la zone"}

# Utilitaires
@router.get("/monsters/search")
async def search_monsters(q: Optional[str] = None, limit: int = 20, db: Session = Depends(get_db)):
    """Recherche des monstres pour l'interface admin"""
    query = "SELECT DISTINCT monster_id, monster_name FROM monster_drops"
    params = {}
    
    if q:
        query += " WHERE monster_name ILIKE :search"
        params["search"] = f"%{q}%"
    
    query += " ORDER BY monster_name LIMIT :limit"
    params["limit"] = limit
    
    results = db.execute(text(query), params).fetchall()
    
    return [
        {"monster_id": row[0], "monster_name": row[1]} 
        for row in results
    ]