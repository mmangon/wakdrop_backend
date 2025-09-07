#!/usr/bin/env python3
"""
Extracteur ZenithWakfu par noms d'items
Extrait les noms des items plutôt que les IDs pour faire un matching par nom
"""

import asyncio
import re
from typing import List, Dict
from playwright.async_api import async_playwright

async def extract_item_names(build_url: str) -> List[Dict[str, str]]:
    """
    Extrait les noms des items équipés depuis ZenithWakfu
    Retourne une liste de dictionnaires avec name et potentiellement d'autres infos
    """
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=True)
    page = await browser.new_page()
    
    try:
        # Navigation 
        await page.goto(build_url, wait_until='domcontentloaded')
        await page.wait_for_timeout(2000)
        
        # Gérer le modal GDPR
        try:
            refuse_btn = await page.wait_for_selector('button:has-text("Ne pas consentir")', timeout=1000)
            if refuse_btn:
                await refuse_btn.click()
                await page.wait_for_timeout(500)
        except:
            pass
        
        items = []
        
        # Chercher les éléments avec des tooltips ou des noms d'items
        # Essayons plusieurs sélecteurs possibles
        selectors_to_try = [
            'img[src*="/items/"]',  # Images d'items
            '[title]',              # Éléments avec titre
            '.item',                # Classes communes pour items
            '.equipment',           # Classes pour équipement
            '[data-name]',          # Attributs data avec nom
        ]
        
        for selector in selectors_to_try:
            try:
                elements = await page.query_selector_all(selector)
                print(f"Trouvé {len(elements)} éléments avec le sélecteur: {selector}")
                
                for elem in elements:
                    try:
                        # Essayer différents attributs pour récupérer le nom
                        name = None
                        
                        # Essayer title
                        title = await elem.get_attribute('title')
                        if title and title.strip():
                            name = title.strip()
                        
                        # Essayer alt
                        if not name:
                            alt = await elem.get_attribute('alt')
                            if alt and alt.strip() and not alt.startswith('items/'):
                                name = alt.strip()
                        
                        # Essayer data-name
                        if not name:
                            data_name = await elem.get_attribute('data-name')
                            if data_name and data_name.strip():
                                name = data_name.strip()
                        
                        # Essayer le texte contenu
                        if not name:
                            text = await elem.text_content()
                            if text and text.strip() and len(text.strip()) > 2:
                                name = text.strip()
                        
                        if name and len(name) > 3:  # Noms valides seulement
                            # Récupérer l'ID depuis src si disponible
                            item_id = None
                            src = await elem.get_attribute('src')
                            if src:
                                match = re.search(r'items/(\d+)\.(webp|png)', src)
                                if match:
                                    item_id = int(match.group(1))
                            
                            items.append({
                                'name': name,
                                'zenith_id': item_id,
                                'selector': selector
                            })
                    except:
                        continue
            except:
                continue
        
        # Dédupliquer par nom
        unique_items = {}
        for item in items:
            name = item['name']
            if name not in unique_items or (unique_items[name]['zenith_id'] is None and item['zenith_id'] is not None):
                unique_items[name] = item
        
        return list(unique_items.values())
        
    finally:
        await browser.close()
        await playwright.stop()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python zenith_name_extractor.py <BUILD_URL>")
        sys.exit(1)
    
    url = sys.argv[1]
    items = asyncio.run(extract_item_names(url))
    
    print(f"✅ {len(items)} items extraits:")
    for item in items:
        zenith_id = f" (ID: {item['zenith_id']})" if item['zenith_id'] else ""
        print(f"  - {item['name']}{zenith_id}")