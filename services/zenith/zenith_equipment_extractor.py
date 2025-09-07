#!/usr/bin/env python3
"""
Extracteur spécialisé pour les équipements ZenithWakfu
Se concentre uniquement sur les slots d'équipement (casque, amulette, plastron, etc.)
"""

import asyncio
import re
from typing import List, Dict
from playwright.async_api import async_playwright

async def extract_equipment_items(build_url: str) -> List[Dict[str, str]]:
    """
    Extrait uniquement les items équipés dans les slots d'équipement
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
        
        # Attendre que la page soit complètement chargée
        await page.wait_for_timeout(2000)
        
        items = []
        
        # Chercher spécifiquement les slots d'équipement
        # Ces sélecteurs ciblent probablement les zones d'équipement
        equipment_selectors = [
            '.equipment-slot',        # Slots d'équipement  
            '.item-slot',            # Slots d'item
            '.gear-slot',            # Slots de gear
            '[data-slot]',           # Slots avec attribut data
            '.slot',                 # Slots génériques
            '.equipped-item',        # Items équipés
            '.gear-item',            # Items de gear
            '.equipment-item'        # Items d'équipement
        ]
        
        # Essayer aussi les sélecteurs d'images d'items avec containers parents
        image_selectors = [
            'img[src*="/items/"]'    # Images d'items
        ]
        
        # 1. D'abord essayer les sélecteurs d'équipement
        for selector in equipment_selectors:
            try:
                elements = await page.query_selector_all(selector)
                print(f"DEBUG: Sélecteur équipement '{selector}' -> {len(elements)} éléments")
                
                for elem in elements:
                    try:
                        item_info = await extract_item_from_element(elem)
                        if item_info:
                            items.append({**item_info, 'source': 'equipment_slot'})
                    except:
                        continue
            except:
                continue
        
        # 2. Si pas assez d'items, essayer les images avec analyse du contexte
        if len(items) < 10:  # Un build complet devrait avoir ~13 items
            try:
                img_elements = await page.query_selector_all('img[src*="/items/"]')
                print(f"DEBUG: Images d'items trouvées: {len(img_elements)}")
                
                for img in img_elements:
                    try:
                        # Analyser le contexte parent pour déterminer si c'est un équipement
                        parent = await img.evaluate_handle('el => el.parentElement')
                        if parent:
                            parent_class = await parent.get_attribute('class') or ''
                            parent_id = await parent.get_attribute('id') or ''
                            
                            # Vérifier si c'est probablement un slot d'équipement
                            is_equipment = any(keyword in (parent_class + ' ' + parent_id).lower() for keyword in [
                                'slot', 'equipment', 'gear', 'item', 'equipped'
                            ])
                            
                            if is_equipment:
                                item_info = await extract_item_from_image(img)
                                if item_info:
                                    items.append({**item_info, 'source': 'equipment_image'})
                    except:
                        continue
            except:
                pass
        
        # Dédupliquer par nom
        unique_items = {}
        for item in items:
            name = item.get('name')
            if name and len(name) > 3 and not any(skip in name.lower() for skip in ['max :', 'abandon', 'accumulation']):
                if name not in unique_items:
                    unique_items[name] = item
        
        return list(unique_items.values())
        
    finally:
        await browser.close()
        await playwright.stop()

async def extract_item_from_element(elem) -> Dict[str, str]:
    """Extrait les infos d'un élément équipement"""
    try:
        # Classes CSS pour la rareté
        class_list = await elem.get_attribute('class') or ''
        rarity = extract_rarity_from_class(class_list)
        
        # Nom de l'item
        name = None
        
        # 1. Attribut title
        title = await elem.get_attribute('title')
        if title and len(title.strip()) > 3:
            name = clean_item_name(title.strip())
        
        # 2. Texte de l'élément
        if not name:
            text = await elem.text_content()
            if text and len(text.strip()) > 3:
                name = clean_item_name(text.strip())
        
        # 3. Image enfant avec alt
        if not name:
            img = await elem.query_selector('img[alt]')
            if img:
                alt = await img.get_attribute('alt')
                if alt and len(alt.strip()) > 3:
                    name = clean_item_name(alt.strip())
        
        if name:
            return {
                'name': name,
                'rarity': rarity,
                'css_classes': class_list[:100]
            }
    except:
        pass
    
    return None

async def extract_item_from_image(img) -> Dict[str, str]:
    """Extrait les infos depuis une image d'item"""
    try:
        # Alt text
        alt = await img.get_attribute('alt')
        name = None
        
        if alt and len(alt.strip()) > 3 and 'items/' not in alt:
            name = clean_item_name(alt.strip())
        
        # Title
        if not name:
            title = await img.get_attribute('title')
            if title and len(title.strip()) > 3:
                name = clean_item_name(title.strip())
        
        # Classes du parent pour la rareté
        parent = await img.evaluate_handle('el => el.parentElement')
        rarity = 'unknown'
        if parent:
            parent_class = await parent.get_attribute('class') or ''
            rarity = extract_rarity_from_class(parent_class)
        
        if name:
            return {
                'name': name,
                'rarity': rarity,
                'css_classes': parent_class[:100] if parent else ''
            }
    except:
        pass
    
    return None

def extract_rarity_from_class(class_str: str) -> str:
    """Extrait la rareté depuis les classes CSS"""
    class_lower = class_str.lower()
    rarities = {
        'mythic': 'mythic',
        'legendary': 'legendary', 
        'epic': 'epic',
        'rare': 'rare',
        'unusual': 'unusual',
        'common': 'common',
        'relic': 'relic'
    }
    
    for keyword, rarity in rarities.items():
        if keyword in class_lower:
            return rarity
    
    return 'unknown'

def clean_item_name(name: str) -> str:
    """Nettoie le nom d'un item"""
    # Retirer les chiffres en début
    name = re.sub(r'^\d+\s*', '', name)
    # Retirer les patterns comme [Max : X]
    name = re.sub(r'\[Max\s*:\s*\d+\]', '', name)
    # Nettoyer les espaces
    name = name.strip()
    
    return name

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python zenith_equipment_extractor.py <BUILD_URL>")
        sys.exit(1)
    
    url = sys.argv[1]
    items = asyncio.run(extract_equipment_items(url))
    
    print(f"\n✅ {len(items)} équipements extraits:")
    for item in items:
        print(f"  - {item['name']} [{item['rarity']}] (source: {item.get('source', 'unknown')})")