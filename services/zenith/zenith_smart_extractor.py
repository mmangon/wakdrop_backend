#!/usr/bin/env python3
"""
Extracteur ZenithWakfu intelligent
Extrait les noms d'items et leur rareté depuis les classes CSS
"""

import asyncio
import re
from typing import List, Dict
from playwright.async_api import async_playwright

async def extract_items_with_rarity(build_url: str) -> List[Dict[str, str]]:
    """
    Extrait les items équipés avec leur nom et rareté
    """
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=True)
    page = await browser.new_page()
    
    try:
        # Navigation
        await page.goto(build_url, wait_until='domcontentloaded')
        await page.wait_for_timeout(3000)
        
        # Gérer le modal GDPR
        try:
            refuse_btn = await page.wait_for_selector('button:has-text("Ne pas consentir")', timeout=2000)
            if refuse_btn:
                await refuse_btn.click()
                await page.wait_for_timeout(500)
        except:
            pass
        
        items = []
        
        # Chercher les conteneurs d'items équipés
        # ZenithWakfu utilise probablement des divs avec classes de rareté
        selectors_to_try = [
            'div[class*="rarity"]',     # Divs avec rareté dans la classe
            'div[class*="item"]',       # Divs d'items
            'div[class*="equipment"]',  # Divs d'équipement
            '.slot',                    # Slots d'équipement
            '[class*="epic"]',          # Items épiques
            '[class*="legendary"]',     # Items légendaires
            '[class*="rare"]',          # Items rares
            '[class*="mythic"]',        # Items mythiques
            '[class*="relic"]',         # Items reliques
        ]
        
        for selector in selectors_to_try:
            try:
                elements = await page.query_selector_all(selector)
                print(f"DEBUG: Sélecteur '{selector}' -> {len(elements)} éléments")
                
                for elem in elements:
                    try:
                        # Récupérer les classes CSS pour la rareté
                        class_list = await elem.get_attribute('class')
                        if not class_list:
                            continue
                        
                        # Extraire la rareté depuis les classes
                        rarity = None
                        rarities = ['mythic', 'legendary', 'epic', 'rare', 'unusual', 'common', 'relic']
                        for r in rarities:
                            if r in class_list.lower():
                                rarity = r
                                break
                        
                        # Chercher le nom de l'item dans l'élément ou ses enfants
                        item_name = None
                        
                        # Essayer différents moyens de récupérer le nom
                        # 1. Attribut title
                        title = await elem.get_attribute('title')
                        if title and len(title.strip()) > 3:
                            item_name = title.strip()
                        
                        # 2. Texte de l'élément
                        if not item_name:
                            text = await elem.text_content()
                            if text and len(text.strip()) > 3 and not text.strip().isdigit():
                                item_name = text.strip()
                        
                        # 3. Chercher dans les enfants img avec alt
                        if not item_name:
                            img = await elem.query_selector('img[alt]')
                            if img:
                                alt = await img.get_attribute('alt')
                                if alt and len(alt.strip()) > 3 and not 'items/' in alt:
                                    item_name = alt.strip()
                        
                        # 4. Chercher un span ou div enfant avec du texte
                        if not item_name:
                            text_elem = await elem.query_selector('span, div, p')
                            if text_elem:
                                text = await text_elem.text_content()
                                if text and len(text.strip()) > 3 and not text.strip().isdigit():
                                    item_name = text.strip()
                        
                        # Vérifier que c'est un nom d'item valide
                        if item_name and len(item_name) > 3:
                            # Nettoyer le nom
                            item_name = re.sub(r'^\d+\s*', '', item_name)  # Retirer chiffres en début
                            item_name = item_name.strip()
                            
                            if len(item_name) > 3:
                                items.append({
                                    'name': item_name,
                                    'rarity': rarity or 'unknown',
                                    'css_classes': class_list,
                                    'selector': selector
                                })
                                print(f"DEBUG: Item trouvé -> {item_name} ({rarity})")
                    except Exception as e:
                        print(f"DEBUG: Erreur sur élément: {e}")
                        continue
            except Exception as e:
                print(f"DEBUG: Erreur sélecteur '{selector}': {e}")
                continue
        
        # Dédupliquer par nom (garder celui avec la meilleure rareté si doublon)
        rarity_priority = {'mythic': 1, 'legendary': 2, 'relic': 3, 'epic': 4, 'rare': 5, 'unusual': 6, 'common': 7, 'unknown': 8}
        
        unique_items = {}
        for item in items:
            name = item['name']
            if name not in unique_items:
                unique_items[name] = item
            else:
                # Garder celui avec la meilleure rareté
                current_priority = rarity_priority.get(unique_items[name]['rarity'], 10)
                new_priority = rarity_priority.get(item['rarity'], 10)
                if new_priority < current_priority:
                    unique_items[name] = item
        
        return list(unique_items.values())
        
    finally:
        await browser.close()
        await playwright.stop()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python zenith_smart_extractor.py <BUILD_URL>")
        sys.exit(1)
    
    url = sys.argv[1]
    items = asyncio.run(extract_items_with_rarity(url))
    
    print(f"\n✅ {len(items)} items uniques extraits:")
    for item in items:
        print(f"  - {item['name']} [{item['rarity']}] (CSS: {item['css_classes'][:50]}...)")