#!/usr/bin/env python3
"""
Script subprocess pour extraire les noms d'items depuis ZenithWakfu
Remplace l'extracteur d'IDs par un extracteur de noms
"""

import asyncio
import sys
import json
from pathlib import Path

# Ajouter le répertoire parent au PYTHONPATH  
sys.path.append(str(Path(__file__).parent.parent.parent))

from services.zenith.zenith_simple_extractor import extract_items_simple
from services.zenith.item_name_matcher import ItemNameMatcher

async def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "URL manquante"}))
        sys.exit(1)
    
    url = sys.argv[1]
    
    try:
        # 1. Extraire les noms depuis ZenithWakfu
        zenith_items = await extract_items_simple(url)
        
        if not zenith_items:
            print(json.dumps({
                "success": False,
                "error": "Aucun item trouvé sur la page Zenith"
            }))
            sys.exit(1)
        
        # 2. Matcher avec notre cache
        matcher = ItemNameMatcher()
        match_results = matcher.match_zenith_items(zenith_items)
        
        # 3. Préparer la réponse
        result = {
            "success": True,
            "extraction_method": "names",
            "zenith_items_found": len(zenith_items),
            "cache_matches": len(match_results['items_found']),
            "item_ids": match_results['valid_item_ids'],
            "items_details": match_results['items_found'],
            "items_missing": match_results['items_missing']
        }
        
        print(json.dumps(result))
        
    except Exception as e:
        result = {
            "success": False,
            "error": str(e)
        }
        print(json.dumps(result))
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())