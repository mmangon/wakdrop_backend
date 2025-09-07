#!/usr/bin/env python3
"""
Extracteur rapide et optimisé pour ZenithWakfu
Extrait uniquement le nécessaire : nom et ID Wakfu des items
"""

import asyncio
import re
from typing import Dict, List, Optional
from playwright.async_api import async_playwright

class ZenithFastExtractor:
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.page = None
        
    async def initialize(self):
        """Initialise le navigateur"""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
        )
        context = await self.browser.new_context()
        self.page = await context.new_page()
        
    async def extract_items(self, build_url: str) -> List[Dict]:
        """
        Extrait rapidement les items d'un build
        
        Returns:
            Liste avec nom et ID Wakfu de chaque item
        """
        # Navigation
        await self.page.goto(build_url, wait_until='domcontentloaded')
        await self.page.wait_for_timeout(2000)
        
        # Gérer le modal GDPR s'il apparaît
        try:
            refuse_button = await self.page.wait_for_selector(
                'button:has-text("Ne pas consentir")',
                timeout=2000
            )
            if refuse_button:
                await refuse_button.click()
                await self.page.wait_for_timeout(500)
        except:
            pass
        
        # Chercher les images d'items
        items_data = []
        item_images = await self.page.query_selector_all('img[src*="/items/"]')
        
        for img in item_images:
            try:
                # Survoler pour déclencher la tooltip
                await img.hover()
                await self.page.wait_for_timeout(300)
                
                # Chercher la tooltip
                tooltip = await self.page.query_selector('div[class*="MuiTooltip-popper"]')
                if tooltip:
                    # Extraire le nom (première ligne du texte)
                    text = await tooltip.inner_text()
                    name = text.split('\n')[0].strip() if text else None
                    
                    # Extraire l'ID depuis le HTML
                    html = await tooltip.inner_html()
                    wakfu_id = self.extract_id_from_html(html)
                    
                    if name and wakfu_id:
                        items_data.append({
                            'name': name,
                            'wakfu_id': wakfu_id
                        })
                
                # Sortir du survol
                await self.page.mouse.move(0, 0)
                
            except:
                continue
        
        return items_data
    
    def extract_id_from_html(self, html: str) -> Optional[int]:
        """Extrait l'ID Wakfu depuis le HTML"""
        # Pattern: alt="items/ID"
        match = re.search(r'alt="items/(\d+)"', html)
        if match:
            return int(match.group(1))
        
        # Pattern alternatif: src="../images/items/ID.webp"
        match = re.search(r'src="[^"]*items/(\d+)\.(webp|png)"', html)
        if match:
            return int(match.group(1))
        
        return None
    
    async def close(self):
        """Ferme le navigateur"""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

async def quick_extract(build_url: str) -> List[Dict]:
    """
    Fonction utilitaire pour extraction rapide
    """
    extractor = ZenithFastExtractor()
    try:
        await extractor.initialize()
        items = await extractor.extract_items(build_url)
        return items
    finally:
        await extractor.close()

if __name__ == "__main__":
    import sys
    import json
    
    if len(sys.argv) < 2:
        print("Usage: python zenith_fast_extractor.py <BUILD_URL>")
        sys.exit(1)
    
    url = sys.argv[1]
    items = asyncio.run(quick_extract(url))
    
    print(f"✅ {len(items)} items extraits:")
    for item in items:
        print(f"  - {item['name']} (ID: {item['wakfu_id']})")
    
    # Sauvegarder en JSON
    with open('zenith_fast_extract.json', 'w', encoding='utf-8') as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
    print(f"\n💾 Sauvegardé dans zenith_fast_extract.json")