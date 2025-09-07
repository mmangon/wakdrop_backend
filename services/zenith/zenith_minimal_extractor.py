#!/usr/bin/env python3
"""
Extracteur ultra-rapide pour ZenithWakfu
Extrait uniquement les IDs Wakfu des items
"""

import asyncio
import re
from typing import List
from playwright.async_api import async_playwright

async def extract_item_ids(build_url: str) -> List[int]:
    """
    Extrait uniquement les IDs Wakfu des items
    Version ultra-rapide sans extraction de noms
    """
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=True)
    page = await browser.new_page()
    
    try:
        # Navigation rapide
        await page.goto(build_url, wait_until='domcontentloaded')
        await page.wait_for_timeout(1000)
        
        # Gérer le modal GDPR
        try:
            refuse_btn = await page.wait_for_selector('button:has-text("Ne pas consentir")', timeout=1000)
            if refuse_btn:
                await refuse_btn.click()
                await page.wait_for_timeout(300)
        except:
            pass
        
        # Récupérer toutes les images d'items d'un coup
        item_images = await page.query_selector_all('img[src*="/items/"]')
        item_ids = set()  # Utiliser un set pour éviter les doublons
        
        # Extraire les IDs directement depuis les attributs src
        for img in item_images:
            try:
                src = await img.get_attribute('src')
                if src:
                    # Pattern: /images/items/ID.webp
                    match = re.search(r'items/(\d+)\.(webp|png)', src)
                    if match:
                        item_ids.add(int(match.group(1)))
            except:
                continue
        
        return list(item_ids)
        
    finally:
        await browser.close()
        await playwright.stop()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python zenith_minimal_extractor.py <BUILD_URL>")
        sys.exit(1)
    
    url = sys.argv[1]
    ids = asyncio.run(extract_item_ids(url))
    
    print(f"✅ {len(ids)} IDs extraits:")
    for item_id in ids:
        print(f"  - {item_id}")
    
    print(f"\n🔢 IDs: {ids}")