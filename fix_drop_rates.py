#!/usr/bin/env python3
"""
Script pour corriger les drop rates en comparant avec les fichiers JSON du bestiaire
"""

import json
import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from collections import defaultdict

# Configuration de la base de données
# Charger les variables d'environnement depuis .env
from pathlib import Path
env_path = Path('/opt/muppy/wakdropbackend/.env')
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            if line.strip() and not line.startswith('#'):
                key, value = line.strip().split('=', 1)
                os.environ[key] = value

DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://muppy:wakfu2024@localhost:5432/wakdrop')
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

def map_rarity_to_id(rarity_text: str) -> int:
    """
    Convertit les raretés français vers IDs numériques CDN
    """
    rarity_map = {
        'qualité commune': 0,
        'commun': 0,
        'inhabituel': 1, 
        'rare': 2,
        'mythique': 3,
        'légendaire': 4,
        'relique': 5,
        'épique': 6,
        'pvp': 7,  # PVP = Souvenir
        'souvenir': 7,
    }
    
    normalized = rarity_text.lower().strip()
    return rarity_map.get(normalized, 0)  # Par défaut: Commun

def load_json_drops():
    """
    Charge tous les drops depuis le fichier JSON du bestiaire avec raretés
    """
    all_drops = defaultdict(dict)  # {monster_id: {item_id: {rate, rarity}}}
    json_file = 'wakfu_bestiaire_complet_20250910_200442.json'
    
    filepath = f'/opt/muppy/wakdropbackend/{json_file}'
    if not os.path.exists(filepath):
        print(f"❌ Fichier non trouvé: {json_file}")
        return all_drops
        
    print(f"📖 Lecture de {json_file}...")
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    for monster in data:
        monster_id = int(monster['id'])
        monster_name = monster['name']
        
        for drop in monster.get('drops', []):
            item_id = int(drop['item_id'])
            # Convertir le pourcentage string en float
            drop_perc = drop['drop_perc'].replace('%', '')
            drop_rate = float(drop_perc)
            
            # Extraire et convertir la rareté
            rarity_text = drop.get('rarity', '')
            rarity_id = map_rarity_to_id(rarity_text)
            
            # Stocker le drop rate + rareté
            if monster_id not in all_drops:
                all_drops[monster_id] = {}
            all_drops[monster_id][item_id] = {
                'rate': drop_rate,
                'monster_name': monster_name,
                'rarity_id': rarity_id,
                'rarity_text': rarity_text
            }
    
    return all_drops

def get_database_drops(session):
    """
    Récupère tous les drops de la base de données
    """
    result = session.execute(text("""
        SELECT monster_id, item_id, drop_rate, monster_name
        FROM monster_drops
        ORDER BY monster_id, item_id
    """))
    
    db_drops = defaultdict(dict)
    for row in result:
        monster_id = row[0]
        item_id = row[1]
        drop_rate = row[2]
        monster_name = row[3]
        
        if monster_id not in db_drops:
            db_drops[monster_id] = {}
        db_drops[monster_id][item_id] = {
            'rate': drop_rate,
            'monster_name': monster_name
        }
    
    return db_drops

def update_items_with_rarity(session, json_drops):
    """
    Met à jour SEULEMENT les items manquants du CDN (obtention_type = 'unknown') avec les raretés du bestiaire
    """
    print("\n🎨 Mise à jour des raretés pour les items manquants du CDN...")
    
    # Créer un mapping item_id -> rarity_id
    item_rarities = {}
    for monster_data in json_drops.values():
        for item_id, item_data in monster_data.items():
            if item_data['rarity_id'] is not None:
                item_rarities[item_id] = {
                    'rarity_id': item_data['rarity_id'],
                    'rarity_text': item_data['rarity_text']
                }
    
    print(f"📦 {len(item_rarities)} items avec rareté trouvés dans le bestiaire")
    
    updated_count = 0
    for item_id, rarity_data in item_rarities.items():
        # Vérifier si l'item existe en cache ET qu'il vient du bestiaire (obtention_type = 'unknown')
        result = session.execute(text("""
            SELECT data_json FROM cached_items 
            WHERE wakfu_id = :item_id AND obtention_type = 'unknown'
        """), {'item_id': item_id})
        
        row = result.fetchone()
        if row:
            data_json = row[0]
            
            # Créer la structure baseParameters si elle n'existe pas
            if 'definition' not in data_json:
                data_json['definition'] = {'id': item_id}
            if 'item' not in data_json['definition']:
                data_json['definition']['item'] = {}
            if 'baseParameters' not in data_json['definition']['item']:
                data_json['definition']['item']['baseParameters'] = {}
            
            # Mettre à jour la rareté
            data_json['definition']['item']['baseParameters']['rarity'] = rarity_data['rarity_id']
            
            # Mettre à jour en base
            session.execute(text("""
                UPDATE cached_items 
                SET data_json = :data_json 
                WHERE wakfu_id = :item_id
            """), {
                'data_json': json.dumps(data_json),
                'item_id': item_id
            })
            
            updated_count += 1
        else:
            # Item n'existe pas, le créer avec la rareté
            item_data = {
                'definition': {
                    'id': item_id,
                    'title': {'fr': f'Item {item_id}'},
                    'item': {
                        'baseParameters': {
                            'rarity': rarity_data['rarity_id']
                        }
                    }
                },
                'title': f'Item {item_id}',
                'description': {'fr': f'Item {item_id} ajouté depuis le bestiaire avec rareté'}
            }
            
            session.execute(text("""
                INSERT INTO cached_items (wakfu_id, data_json, obtention_type, last_updated)
                VALUES (:wakfu_id, :data_json, 'unknown', NOW())
                ON CONFLICT (wakfu_id) DO NOTHING
            """), {
                'wakfu_id': item_id,
                'data_json': json.dumps(item_data)
            })
    
    session.commit()
    print(f"✅ {updated_count} items manquants du CDN mis à jour avec raretés")
    print(f"🔒 Items du CDN officiel conservent leurs raretés originales")

def compare_and_fix_drops():
    """
    Compare les drops JSON avec la base et applique les corrections + raretés
    """
    session = Session()
    
    try:
        # Charger les données
        print("\n🔍 Chargement des données...")
        json_drops = load_json_drops()
        db_drops = get_database_drops(session)
        
        print(f"✅ JSON: {len(json_drops)} monstres")
        print(f"✅ Base: {len(db_drops)} monstres")
        
        # Comparer et corriger
        corrections = []
        new_drops = []
        
        for monster_id, items in json_drops.items():
            for item_id, json_data in items.items():
                json_rate = json_data['rate']
                monster_name = json_data['monster_name']
                
                # Vérifier si le drop existe en base
                if monster_id in db_drops and item_id in db_drops[monster_id]:
                    db_rate = db_drops[monster_id][item_id]['rate']
                    
                    # Si les taux sont différents, corriger
                    if abs(db_rate - json_rate) > 0.001:  # Tolérance pour les flottants
                        corrections.append({
                            'monster_id': monster_id,
                            'item_id': item_id,
                            'old_rate': db_rate,
                            'new_rate': json_rate,
                            'monster_name': monster_name
                        })
                else:
                    # Le drop n'existe pas, l'ajouter
                    new_drops.append({
                        'monster_id': monster_id,
                        'item_id': item_id,
                        'drop_rate': json_rate,
                        'monster_name': monster_name
                    })
        
        # Appliquer les corrections
        corrections_applied = False
        drops_added = False
        
        if corrections:
            print(f"\n🔧 Application de {len(corrections)} corrections...")
            for corr in corrections[:10]:  # Afficher les 10 premières
                print(f"  - Monster {corr['monster_id']} ({corr['monster_name']}), Item {corr['item_id']}: {corr['old_rate']}% → {corr['new_rate']}%")
            
            if len(corrections) > 10:
                print(f"  ... et {len(corrections) - 10} autres corrections")
            
            # Appliquer automatiquement les corrections
            print("\n🔧 Application automatique des corrections...")
            for corr in corrections:
                session.execute(text("""
                    UPDATE monster_drops 
                    SET drop_rate = :new_rate 
                    WHERE monster_id = :monster_id AND item_id = :item_id
                """), {
                    'new_rate': corr['new_rate'],
                    'monster_id': corr['monster_id'],
                    'item_id': corr['item_id']
                })
            session.commit()
            corrections_applied = True
            print(f"✅ {len(corrections)} corrections appliquées!")
        else:
            print("\n✅ Aucune correction nécessaire pour les drops existants!")
        
        # Ajouter les nouveaux drops
        if new_drops:
            print(f"\n➕ {len(new_drops)} nouveaux drops trouvés")
            for drop in new_drops[:5]:
                print(f"  - Monster {drop['monster_id']} ({drop['monster_name']}), Item {drop['item_id']}: {drop['drop_rate']}%")
            
            if len(new_drops) > 5:
                print(f"  ... et {len(new_drops) - 5} autres")
            
            print("\n➕ Ajout automatique des nouveaux drops...")
            for drop in new_drops:
                session.execute(text("""
                    INSERT INTO monster_drops (monster_id, item_id, drop_rate, monster_name)
                    VALUES (:monster_id, :item_id, :drop_rate, :monster_name)
                    ON CONFLICT (monster_id, item_id) DO NOTHING
                """), drop)
            session.commit()
            drops_added = True
            print(f"✅ {len(new_drops)} nouveaux drops ajoutés!")
        
        # Mettre à jour les raretés
        update_items_with_rarity(session, json_drops)
        
        # Statistiques finales
        print("\n📊 Résumé:")
        print(f"  - Corrections appliquées: {len(corrections) if corrections_applied else 0}")
        print(f"  - Nouveaux drops ajoutés: {len(new_drops) if drops_added else 0}")
        print(f"  - Items avec raretés mis à jour")
        
    except Exception as e:
        session.rollback()
        print(f"\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()

if __name__ == "__main__":
    print("🚀 Correction des drop rates depuis les fichiers JSON")
    print("=" * 50)
    compare_and_fix_drops()