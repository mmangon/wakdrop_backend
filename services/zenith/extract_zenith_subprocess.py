#!/usr/bin/env python3
"""
Script subprocess pour extraire les IDs depuis ZenithWakfu
Evite les problèmes de Playwright dans l'API
"""

import asyncio
import sys
import json
import os
from pathlib import Path

# Ajouter le répertoire parent au PYTHONPATH
sys.path.append(str(Path(__file__).parent.parent.parent))

from services.zenith.zenith_minimal_extractor import extract_item_ids

async def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "URL manquante"}))
        sys.exit(1)
    
    url = sys.argv[1]
    
    try:
        item_ids = await extract_item_ids(url)
        result = {
            "success": True,
            "item_ids": item_ids,
            "count": len(item_ids)
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