"""
Service pour gérer les données de drop (stockage et récupération)
"""

from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_
from core.database import SessionLocal
from models.cache import MonsterDrop, CachedMonster
from models.zones import Zone, MonsterZone
# from services.wakfu_scraper import WakfuScraper  # Module supprimé
import json

class DropManager:
    def __init__(self):
        # self.scraper = WakfuScraper(delay_min=2.0, delay_max=4.0)  # Module supprimé
        pass
    
    async def import_drops_from_scraper(self, item_ids: List[int]) -> Dict:
        """
        Importe les données de drop pour une liste d'items
        
        Args:
            item_ids: Liste des IDs d'items à scraper
            
        Returns:
            Résumé de l'import
        """
        db = SessionLocal()
        try:
            results = {
                'items_processed': 0,
                'drops_added': 0,
                'monsters_added': 0,
                'errors': []
            }
            
            for item_id in item_ids:
                try:
                    # Scraper les données de l'item
                    item_data = await self.scraper.get_item_details(item_id)
                    if not item_data:
                        results['errors'].append(f"Item {item_id} non trouvé")
                        continue
                    
                    results['items_processed'] += 1
                    
                    # Traiter chaque drop
                    for drop in item_data.get('drops', []):
                        if not drop.get('monster_id'):
                            continue
                        
                        # Vérifier si le monstre existe en cache
                        monster = db.query(CachedMonster).filter(
                            CachedMonster.wakfu_id == drop['monster_id']
                        ).first()
                        
                        if not monster:
                            # Scraper les détails du monstre
                            monster_details = await self.scraper.get_monster_details(drop['monster_id'])
                            if monster_details:
                                # Créer le monstre en cache
                                monster = CachedMonster(
                                    wakfu_id=drop['monster_id'],
                                    name=monster_details['name'],
                                    level=monster_details.get('level'),
                                    family_id=None,  # À implémenter si nécessaire
                                    data_json=monster_details
                                )
                                db.add(monster)
                                db.flush()
                                results['monsters_added'] += 1
                        
                        # Vérifier si le drop existe déjà
                        existing_drop = db.query(MonsterDrop).filter(
                            and_(
                                MonsterDrop.monster_id == drop['monster_id'],
                                MonsterDrop.item_id == item_id
                            )
                        ).first()
                        
                        if existing_drop:
                            # Mettre à jour le taux si différent
                            if drop.get('drop_rate') and existing_drop.drop_rate != drop['drop_rate']:
                                existing_drop.drop_rate = drop['drop_rate']
                        else:
                            # Créer le nouveau drop
                            new_drop = MonsterDrop(
                                monster_id=drop['monster_id'],
                                monster_name=drop.get('monster_name', 'Unknown'),
                                item_id=item_id,
                                drop_rate=drop.get('drop_rate', 0.0),
                                zone_name=None  # À récupérer depuis monster_details si disponible
                            )
                            db.add(new_drop)
                            results['drops_added'] += 1
                    
                    db.commit()
                    
                except Exception as e:
                    db.rollback()
                    results['errors'].append(f"Erreur item {item_id}: {str(e)}")
                    continue
            
            return results
            
        finally:
            db.close()
            await self.scraper.close()
    
    def get_drops_for_items(self, item_ids: List[int]) -> Dict:
        """
        Récupère toutes les données de drop pour une liste d'items
        
        Args:
            item_ids: Liste des IDs d'items
            
        Returns:
            Dictionnaire organisé par item avec les infos de drop
        """
        db = SessionLocal()
        try:
            drops_data = {}
            
            for item_id in item_ids:
                drops = db.query(MonsterDrop).filter(
                    MonsterDrop.item_id == item_id
                ).order_by(MonsterDrop.drop_rate.desc()).all()
                
                drops_data[item_id] = {
                    'total_sources': len(drops),
                    'drops': []
                }
                
                for drop in drops:
                    # Récupérer les infos du monstre si en cache
                    monster = db.query(CachedMonster).filter(
                        CachedMonster.wakfu_id == drop.monster_id
                    ).first()
                    
                    # Récupérer les zones depuis notre table de zones
                    monster_zones = db.query(MonsterZone, Zone).join(
                        Zone, MonsterZone.zone_id == Zone.id
                    ).filter(MonsterZone.monster_id == drop.monster_id).all()
                    
                    zones_list = [zone.name for _, zone in monster_zones]
                    
                    drop_info = {
                        'monster_id': drop.monster_id,
                        'monster_name': drop.monster_name,
                        'monster_level': monster.level if monster else None,
                        'drop_rate': drop.drop_rate,
                        'zone_name': drop.zone_name,
                        'zones': zones_list
                    }
                    
                    drops_data[item_id]['drops'].append(drop_info)
            
            return drops_data
            
        finally:
            db.close()
    
    def get_farm_roadmap(self, item_ids: List[int]) -> Dict:
        """
        Génère une roadmap de farm optimisée pour une liste d'items
        
        Args:
            item_ids: Liste des IDs d'items à farmer
            
        Returns:
            Roadmap organisée par zones/monstres avec structure pliable
        """
        drops_data = self.get_drops_for_items(item_ids)
        
        # Organiser par zones
        zones_map = {}
        monsters_map = {}
        
        for item_id, item_drops in drops_data.items():
            for drop in item_drops['drops']:
                monster_id = drop['monster_id']
                
                # Grouper par monstre
                if monster_id not in monsters_map:
                    monsters_map[monster_id] = {
                        'name': drop['monster_name'],
                        'level': drop['monster_level'],
                        'zones': drop.get('zones', []),
                        'items': []
                    }
                
                monsters_map[monster_id]['items'].append({
                    'item_id': item_id,
                    'drop_rate': drop['drop_rate']
                })
                
                # Grouper par zones
                zones = drop.get('zones', [drop.get('zone_name', 'Zone inconnue')])
                for zone in zones:
                    if zone not in zones_map:
                        zones_map[zone] = {
                            'monsters': {},
                            'total_items': 0,
                            'avg_drop_rate': 0,
                            'expanded': False  # Pour l'interface pliable
                        }
                    # Ajouter le monstre dans la zone avec ses détails
                    zones_map[zone]['monsters'][monster_id] = {
                        'name': drop['monster_name'],
                        'level': drop['monster_level'],
                        'items': []
                    }
        
        # Ajouter les items à chaque monstre dans chaque zone
        for zone, zone_data in zones_map.items():
            total_rate = 0
            total_items = 0
            
            for monster_id in zone_data['monsters']:
                if monster_id in monsters_map:
                    monster_items = monsters_map[monster_id]['items']
                    zone_data['monsters'][monster_id]['items'] = monster_items
                    total_items += len(monster_items)
                    total_rate += sum(item['drop_rate'] for item in monster_items)
            
            zone_data['total_items'] = total_items
            zone_data['avg_drop_rate'] = total_rate / total_items if total_items > 0 else 0
        
        # Trier les zones par efficacité (plus d'items, meilleur taux)
        sorted_zones = sorted(
            zones_map.items(),
            key=lambda x: (x[1]['total_items'], x[1]['avg_drop_rate']),
            reverse=True
        )
        
        # Créer la structure finale avec zones organisées
        zones_organized = []
        for zone_name, zone_data in sorted_zones:
            zones_organized.append({
                'name': zone_name,
                'total_items': zone_data['total_items'],
                'avg_drop_rate': zone_data['avg_drop_rate'],
                'expanded': zone_data['expanded'],
                'monsters': [
                    {
                        'id': monster_id,
                        'name': monster_info['name'],
                        'level': monster_info['level'],
                        'items': monster_info['items']
                    }
                    for monster_id, monster_info in zone_data['monsters'].items()
                ]
            })
        
        return {
            'zones_organized': zones_organized,  # Nouvelle structure pour l'interface pliable
            'zones': dict(sorted_zones),  # Garder l'ancienne structure pour compatibilité
            'monsters': monsters_map,
            'summary': {
                'total_items': len(item_ids),
                'total_zones': len(zones_map),
                'total_monsters': len(monsters_map)
            }
        }
    
    async def import_from_file(self, filepath: str) -> Dict:
        """
        Importe les données de drop depuis un fichier JSON
        
        Args:
            filepath: Chemin vers le fichier JSON
            
        Returns:
            Résumé de l'import
        """
        db = SessionLocal()
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            results = {
                'drops_added': 0,
                'drops_updated': 0,
                'errors': []
            }
            
            for item in data:
                if not isinstance(item, dict):
                    continue
                
                item_id = item.get('item_id')
                if not item_id:
                    continue
                
                for drop in item.get('drops', []):
                    try:
                        monster_id = drop.get('monster_id')
                        if not monster_id:
                            continue
                        
                        # Vérifier si le drop existe
                        existing = db.query(MonsterDrop).filter(
                            and_(
                                MonsterDrop.monster_id == monster_id,
                                MonsterDrop.item_id == item_id
                            )
                        ).first()
                        
                        if existing:
                            existing.drop_rate = drop.get('drop_rate', existing.drop_rate)
                            existing.monster_name = drop.get('monster_name', existing.monster_name)
                            results['drops_updated'] += 1
                        else:
                            new_drop = MonsterDrop(
                                monster_id=monster_id,
                                monster_name=drop.get('monster_name', 'Unknown'),
                                item_id=item_id,
                                drop_rate=drop.get('drop_rate', 0.0),
                                zone_name=drop.get('zone_name')
                            )
                            db.add(new_drop)
                            results['drops_added'] += 1
                        
                    except Exception as e:
                        results['errors'].append(f"Erreur drop {monster_id}->{item_id}: {str(e)}")
            
            db.commit()
            return results
            
        except Exception as e:
            db.rollback()
            return {'error': str(e)}
        finally:
            db.close()

drop_manager = DropManager()