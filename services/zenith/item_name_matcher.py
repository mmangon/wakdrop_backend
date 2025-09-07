#!/usr/bin/env python3
"""
Matcher intelligent pour les noms d'items ZenithWakfu
Recherche les items dans notre cache par nom français avec scoring de similarité
"""

from typing import List, Dict, Optional
from difflib import SequenceMatcher
import re
import sys
import os
from pathlib import Path

# Ajouter le répertoire parent au PYTHONPATH
sys.path.append(str(Path(__file__).parent.parent.parent))

from sqlalchemy.orm import Session
from core.database import SessionLocal
from models.cache import CachedItem

class ItemNameMatcher:
    def __init__(self):
        self.db = SessionLocal()
        self._cache_items = None
    
    def __del__(self):
        if self.db:
            self.db.close()
    
    def get_cache_items(self):
        """Récupère tous les items du cache (avec lazy loading)"""
        if self._cache_items is None:
            items = self.db.query(CachedItem).all()
            self._cache_items = []
            
            for item in items:
                try:
                    name_fr = item.data_json.get('title', {}).get('fr', '')
                    if name_fr:
                        self._cache_items.append({
                            'wakfu_id': item.wakfu_id,
                            'name': name_fr,
                            'obtention_type': item.obtention_type,
                            'data': item.data_json
                        })
                except:
                    continue
        
        return self._cache_items
    
    def find_best_matches(self, zenith_name: str, zenith_rarity: str = None, max_results: int = 5) -> List[Dict]:
        """
        Trouve les meilleurs matches pour un nom d'item Zenith
        """
        cache_items = self.get_cache_items()
        candidates = []
        
        # Nettoyer le nom recherché
        clean_zenith_name = self.clean_name_for_matching(zenith_name)
        
        for item in cache_items:
            clean_cache_name = self.clean_name_for_matching(item['name'])
            
            # Calculer différents scores de similarité
            scores = self.calculate_similarity_scores(clean_zenith_name, clean_cache_name, zenith_name, item['name'])
            
            # Score final pondéré
            final_score = (
                scores['exact'] * 2.0 +         # Match exact = priorité maximale
                scores['substring'] * 1.5 +     # Sous-chaîne
                scores['sequence'] * 1.0 +      # Similarité séquentielle
                scores['words'] * 0.8           # Mots en commun
            ) / 5.3
            
            # Bonus si la rareté correspond (si disponible)
            if zenith_rarity and zenith_rarity != 'unknown':
                # TODO: Ajouter mapping rareté si nécessaire
                pass
            
            if final_score > 0.1:  # Seuil minimum
                candidates.append({
                    'wakfu_id': item['wakfu_id'],
                    'name': item['name'],
                    'obtention_type': item['obtention_type'],
                    'score': final_score,
                    'scores_detail': scores,
                    'zenith_name': zenith_name
                })
        
        # Trier par score décroissant
        candidates.sort(key=lambda x: x['score'], reverse=True)
        
        return candidates[:max_results]
    
    def calculate_similarity_scores(self, clean_zenith: str, clean_cache: str, orig_zenith: str, orig_cache: str) -> Dict[str, float]:
        """Calcule différents scores de similarité"""
        scores = {}
        
        # 1. Match exact (nettoyé)
        scores['exact'] = 1.0 if clean_zenith == clean_cache else 0.0
        
        # 2. Match exact original
        if scores['exact'] == 0:
            scores['exact'] = 1.0 if orig_zenith.lower() == orig_cache.lower() else 0.0
        
        # 3. Sous-chaîne
        if clean_zenith in clean_cache or clean_cache in clean_zenith:
            scores['substring'] = min(len(clean_zenith), len(clean_cache)) / max(len(clean_zenith), len(clean_cache))
        else:
            scores['substring'] = 0.0
        
        # 4. Similarité séquentielle (difflib)
        scores['sequence'] = SequenceMatcher(None, clean_zenith, clean_cache).ratio()
        
        # 5. Mots en commun
        zenith_words = set(clean_zenith.split())
        cache_words = set(clean_cache.split())
        if zenith_words and cache_words:
            common_words = zenith_words & cache_words
            scores['words'] = len(common_words) / max(len(zenith_words), len(cache_words))
        else:
            scores['words'] = 0.0
        
        return scores
    
    def clean_name_for_matching(self, name: str) -> str:
        """Nettoie un nom pour améliorer le matching"""
        if not name:
            return ''
        
        # Convertir en minuscules
        name = name.lower()
        
        # Retirer la ponctuation et caractères spéciaux
        name = re.sub(r'[^\w\s]', ' ', name)
        
        # Retirer les mots de niveau
        name = re.sub(r'\b(niv|niveau|lvl|level)\s*\.?\s*\d+\b', '', name)
        
        # Retirer les chiffres isolés
        name = re.sub(r'\b\d+\b', '', name)
        
        # Normaliser les espaces
        name = re.sub(r'\s+', ' ', name).strip()
        
        return name
    
    def match_zenith_items(self, zenith_items: List[Dict[str, str]]) -> Dict:
        """
        Matche une liste d'items Zenith avec notre cache
        Retourne un dictionnaire avec items trouvés et manquants
        """
        results = {
            'items_found': [],
            'items_missing': [],
            'valid_item_ids': []
        }
        
        for zenith_item in zenith_items:
            zenith_name = zenith_item.get('name', '')
            zenith_rarity = zenith_item.get('rarity', 'unknown')
            
            if not zenith_name or len(zenith_name) < 3:
                continue
            
            # Chercher les meilleurs matches
            matches = self.find_best_matches(zenith_name, zenith_rarity, max_results=3)
            
            if matches and matches[0]['score'] > 0.6:  # Seuil de confiance
                best_match = matches[0]
                
                results['items_found'].append({
                    'wakfu_id': best_match['wakfu_id'],
                    'name': best_match['name'],
                    'zenith_name': zenith_name,
                    'zenith_rarity': zenith_rarity,  # 🔥 Ajouter la rareté ZenithWakfu
                    'match_score': best_match['score'],
                    'obtention_type': best_match['obtention_type']
                })
                
                results['valid_item_ids'].append(best_match['wakfu_id'])
                
                print(f"✅ MATCH: '{zenith_name}' -> '{best_match['name']}' (score: {best_match['score']:.2f})", file=sys.stderr)
            else:
                results['items_missing'].append(f"Item: {zenith_name}")
                print(f"❌ MISS: '{zenith_name}' (meilleur score: {matches[0]['score']:.2f} si matches sinon 0.00)", file=sys.stderr)
        
        return results

def test_matcher():
    """Test du matcher avec quelques exemples"""
    matcher = ItemNameMatcher()
    
    # Test avec les items extraits de Zenith
    test_items = [
        {'name': 'Minithar', 'rarity': 'rare'},
        {'name': 'Heaume du Chevalier Creux', 'rarity': 'legendary'},
        {'name': 'Épée Céleste', 'rarity': 'epic'}
    ]
    
    results = matcher.match_zenith_items(test_items)
    
    print(f"\n📊 Résultats du test:")
    print(f"Items trouvés: {len(results['items_found'])}")
    print(f"Items manquants: {len(results['items_missing'])}")
    
    return results

if __name__ == "__main__":
    test_matcher()