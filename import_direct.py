#!/usr/bin/env python3
"""
Import direct des fichiers JSON en base de données
"""
import json
import sys
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_

# Import des modèles et DB
from core.database import SessionLocal, engine
from models.cache import Base, MonsterDrop, CachedMonster

def import_monsters_json(file_path: str):
    """Importe directement un fichier JSON de monstres en base"""
    
    # Créer les tables si nécessaire
    Base.metadata.create_all(bind=engine)
    
    # Ouvrir session DB
    db = SessionLocal()
    
    try:
        print(f"📁 Lecture de {file_path}...")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            monsters = json.load(f)
        
        print(f"✅ {len(monsters)} monstres chargés")
        
        stats = {
            'monsters_processed': 0,
            'monsters_added': 0,
            'drops_added': 0,
            'drops_updated': 0,
            'errors': []
        }
        
        for monster_data in monsters:
            try:
                # Extraire les infos du monstre
                monster_id = int(monster_data.get('id'))
                monster_name = monster_data.get('name', 'Unknown')
                monster_level = monster_data.get('level')
                monster_url = monster_data.get('url', '')
                
                stats['monsters_processed'] += 1
                
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
                            'imported_at': datetime.now().isoformat()
                        }
                    )
                    db.add(cached_monster)
                    stats['monsters_added'] += 1
                
                # Traiter les drops
                for drop_data in monster_data.get('drops', []):
                    try:
                        item_id = int(drop_data.get('item_id'))
                        item_name = drop_data.get('item_name', '')
                        
                        # Gérer drop_perc ("25%") ou drop_rate (25.5)
                        drop_rate = None
                        if 'drop_rate' in drop_data:
                            drop_rate = float(drop_data['drop_rate'])
                        elif 'drop_perc' in drop_data:
                            # Convertir "25%" en 25.0
                            perc_str = drop_data['drop_perc'].replace('%', '').strip()
                            drop_rate = float(perc_str)
                        
                        if drop_rate is None:
                            continue
                        
                        # Vérifier si le drop existe
                        existing_drop = db.query(MonsterDrop).filter(
                            and_(
                                MonsterDrop.monster_id == monster_id,
                                MonsterDrop.item_id == item_id
                            )
                        ).first()
                        
                        if existing_drop:
                            # Mettre à jour
                            if abs(existing_drop.drop_rate - drop_rate) > 0.01:
                                existing_drop.drop_rate = drop_rate
                                stats['drops_updated'] += 1
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
                            stats['drops_added'] += 1
                    
                    except (ValueError, TypeError) as e:
                        stats['errors'].append(f"Drop invalide pour {monster_name}: {str(e)}")
                        continue
                
                # Commit par monstre pour éviter les gros commits
                if stats['monsters_processed'] % 50 == 0:
                    db.commit()
                    print(f"   📈 {stats['monsters_processed']} monstres traités...")
            
            except (ValueError, TypeError) as e:
                stats['errors'].append(f"Monstre invalide {monster_data.get('id', '?')}: {str(e)}")
                continue
        
        # Commit final
        db.commit()
        
        print(f"\n✅ Import terminé:")
        print(f"   • Monstres traités: {stats['monsters_processed']}")
        print(f"   • Nouveaux monstres: {stats['monsters_added']}")
        print(f"   • Nouveaux drops: {stats['drops_added']}")
        print(f"   • Drops mis à jour: {stats['drops_updated']}")
        print(f"   • Erreurs: {len(stats['errors'])}")
        
        if stats['errors'][:5]:  # Afficher max 5 erreurs
            print(f"\n⚠️ Premières erreurs:")
            for error in stats['errors'][:5]:
                print(f"   • {error}")
        
        return True
        
    except Exception as e:
        db.rollback()
        print(f"❌ Erreur fatale: {e}")
        return False
    
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python import_direct.py fichier.json")
        sys.exit(1)
    
    file_path = sys.argv[1]
    success = import_monsters_json(file_path)
    sys.exit(0 if success else 1)