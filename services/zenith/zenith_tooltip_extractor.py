#!/usr/bin/env python3
"""
Extracteur ZenithWakfu basé sur les tooltips
Utilise la structure DOM identifiée dans les screenshots
"""

import asyncio
import re
from typing import List, Dict
from playwright.async_api import async_playwright

async def extract_items_from_tooltips(build_url: str) -> List[Dict[str, str]]:
    """
    Extrait les items en se basant sur les tooltips ZenithWakfu
    Structure identifiée:
    - .tooltip-main-block.tooltip-main-rarity.tooltip-main-rarity-[rarity]
    - .tooltip-title.[rarity]-item-name
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
        
        # Déclencher les tooltips en survolant les images d'items
        await trigger_tooltips(page)
        
        items = []
        
        # Chercher les tooltips d'items avec plus de sélecteurs
        tooltip_selectors = [
            '.tooltip-main-block[class*="tooltip-main-rarity"]',  # Tooltips avec rareté
            '.tooltip-main-block',                                # Tous les tooltips
            '[class*="tooltip-title"]',                          # Éléments de titre
            '[class*="tooltip-main"]',                           # Autres éléments tooltip
            '.tooltip',                                          # Sélecteur générique tooltip
            '[class*="item-tooltip"]',                           # Tooltips spécifiques aux items
            '[class*="equipment"]',                              # Éléments d'équipement
        ]
        
        for selector in tooltip_selectors:
            try:
                elements = await page.query_selector_all(selector)
                print(f"DEBUG: Sélecteur tooltip '{selector}' -> {len(elements)} éléments")
                
                for elem in elements:
                    try:
                        item_info = await extract_item_from_tooltip(elem)
                        if item_info and item_info['name'] and len(item_info['name']) > 3:
                            items.append(item_info)
                            print(f"DEBUG: Item extrait -> {item_info['name']} [{item_info['rarity']}]")
                    except Exception as e:
                        print(f"DEBUG: Erreur extraction tooltip: {e}")
                        continue
            except Exception as e:
                print(f"DEBUG: Erreur sélecteur '{selector}': {e}")
                continue
        
        # Si peu d'items trouvés, essayer plusieurs approches alternatives
        if len(items) < 8:  # Un build complet devrait avoir plus de 8 items
            print("DEBUG: Peu d'items trouvés, essai approches alternatives...")
            alt_items = await extract_items_alternative(page)
            items.extend(alt_items)
            
            # Essayer une extraction encore plus agressive
            if len(items) < 8:
                print("DEBUG: Essai extraction agressive...")
                aggressive_items = await extract_items_aggressive(page)
                items.extend(aggressive_items)
        
        # Dédupliquer par nom
        unique_items = {}
        for item in items:
            name = item['name']
            if name not in unique_items:
                unique_items[name] = item
        
        return list(unique_items.values())
        
    finally:
        await browser.close()
        await playwright.stop()

async def trigger_tooltips(page):
    """Déclenche les tooltips en survolant les images d'items"""
    try:
        # Trouver toutes les images d'items
        img_elements = await page.query_selector_all('img[src*="/items/"]')
        print(f"DEBUG: Déclenchement tooltips sur {len(img_elements)} images")
        
        # Survoler TOUTES les images pour déclencher les tooltips
        for i, img in enumerate(img_elements):  # Pas de limite, on veut tous les items
            try:
                await img.hover()
                await page.wait_for_timeout(300)  # Délai un peu plus long pour s'assurer que le tooltip se charge
            except:
                continue
                
        # Essayer aussi de survoler les conteneurs d'items
        item_containers = await page.query_selector_all('.item-slot, [class*="item"], [class*="slot"]')
        print(f"DEBUG: Déclenchement tooltips sur {len(item_containers)} conteneurs")
        
        for container in item_containers[:20]:  # Limiter les conteneurs pour éviter trop d'attente
            try:
                await container.hover()
                await page.wait_for_timeout(200)
            except:
                continue
                
    except Exception as e:
        print(f"DEBUG: Erreur déclenchement tooltips: {e}")

async def extract_item_from_tooltip(elem) -> Dict[str, str]:
    """Extrait les infos depuis un élément tooltip"""
    try:
        # Classes CSS pour identifier la rareté
        class_list = await elem.get_attribute('class') or ''
        rarity = extract_rarity_from_classes(class_list)
        
        # Chercher le nom dans différents endroits
        name = None
        
        # 1. Chercher .tooltip-title
        title_elem = await elem.query_selector('.tooltip-title, [class*="tooltip-title"]')
        if title_elem:
            name = await title_elem.text_content()
            if name:
                name = name.strip()
        
        # 2. Si pas trouvé, chercher dans les classes *-item-name
        if not name:
            name_elem = await elem.query_selector('[class*="-item-name"]')
            if name_elem:
                name = await name_elem.text_content()
                if name:
                    name = name.strip()
        
        # 3. Dernier recours : texte de l'élément
        if not name:
            text = await elem.text_content()
            if text:
                # Prendre la première ligne non vide
                lines = [line.strip() for line in text.split('\n') if line.strip()]
                if lines:
                    name = lines[0]
        
        # Nettoyer le nom
        if name:
            name = clean_item_name(name)
            
            if len(name) > 3:
                return {
                    'name': name,
                    'rarity': rarity,
                    'css_classes': class_list[:100]
                }
    except Exception as e:
        print(f"DEBUG: Erreur extraction élément: {e}")
    
    return {}

async def extract_items_alternative(page) -> List[Dict[str, str]]:
    """Approche alternative si les tooltips ne marchent pas"""
    items = []
    
    try:
        # Chercher tous les éléments avec des classes de rareté
        rarity_classes = ['legendary', 'epic', 'rare', 'mythic', 'relic', 'unusual', 'common']
        
        for rarity in rarity_classes:
            try:
                elements = await page.query_selector_all(f'[class*="{rarity}"]')
                print(f"DEBUG: Rareté '{rarity}' -> {len(elements)} éléments")
                
                for elem in elements:
                    try:
                        text = await elem.text_content()
                        if text and len(text.strip()) > 3:
                            clean_name = clean_item_name(text.strip())
                            if len(clean_name) > 3 and is_likely_item_name(clean_name):
                                items.append({
                                    'name': clean_name,
                                    'rarity': rarity,
                                    'css_classes': await elem.get_attribute('class') or ''
                                })
                    except:
                        continue
            except:
                continue
    except Exception as e:
        print(f"DEBUG: Erreur approche alternative: {e}")
    
    return items

async def extract_items_aggressive(page) -> List[Dict[str, str]]:
    """Extraction ciblée sur les éléments de build visibles"""
    items = []
    
    try:
        # Chercher spécifiquement dans les zones d'équipement
        equipment_selectors = [
            '[class*="equipment"]',
            '[class*="item"]',
            '[class*="slot"]',
            '[alt*="items"]',
            'img[src*="items"]',  # Images d'items
        ]
        
        processed_names = set()
        
        for selector in equipment_selectors:
            try:
                elements = await page.query_selector_all(selector)
                print(f"DEBUG: Sélecteur équipement '{selector}' -> {len(elements)} éléments")
                
                for elem in elements[:30]:  # Limiter à 30 par sélecteur
                    try:
                        # Chercher le texte dans l'élément et ses enfants
                        texts_to_check = []
                        
                        # Text content de l'élément
                        text = await elem.text_content()
                        if text and text.strip():
                            texts_to_check.append(text.strip())
                        
                        # Alt et title des images
                        alt = await elem.get_attribute('alt')
                        title = await elem.get_attribute('title')
                        if alt:
                            texts_to_check.append(alt)
                        if title:
                            texts_to_check.append(title)
                        
                        # Vérifier chaque texte
                        for text in texts_to_check:
                            if len(text) < 4 or len(text) > 80:
                                continue
                                
                            clean_name = clean_item_name(text)
                            if clean_name in processed_names:
                                continue
                                
                            if is_likely_item_name(clean_name):
                                processed_names.add(clean_name)
                                
                                class_attr = await elem.get_attribute('class') or ''
                                rarity = extract_rarity_from_classes(class_attr)
                                
                                items.append({
                                    'name': clean_name,
                                    'rarity': rarity,
                                    'css_classes': class_attr[:100],
                                    'extraction_method': 'focused'
                                })
                                print(f"DEBUG: Item ciblé trouvé -> {clean_name} [{rarity}]")
                                
                    except:
                        continue
                        
            except Exception as e:
                print(f"DEBUG: Erreur sélecteur '{selector}': {e}")
                continue
                
        return items[:15]  # Limiter à 15 items maximum
        
    except Exception as e:
        print(f"DEBUG: Erreur extraction ciblée: {e}")
        return []

def extract_rarity_from_classes(class_str: str) -> str:
    """Extrait la rareté depuis les classes CSS"""
    class_lower = class_str.lower()
    
    # Ordre de priorité pour les raretés
    rarities = ['mythic', 'legendary', 'relic', 'epic', 'rare', 'unusual', 'common']
    
    for rarity in rarities:
        if rarity in class_lower:
            return rarity
    
    return 'unknown'

def clean_item_name(name: str) -> str:
    """Nettoie le nom d'un item"""
    if not name:
        return ''
    
    # Retirer les patterns indésirables
    name = re.sub(r'^\d+\s*', '', name)  # Chiffres en début
    name = re.sub(r'\[Max\s*:\s*\d+\]', '', name)  # [Max : X]
    name = re.sub(r'\s+', ' ', name)  # Espaces multiples
    name = name.strip()
    
    return name

def is_likely_item_name(name: str) -> bool:
    """Détermine si un nom ressemble à un nom d'item"""
    if not name or len(name) < 4 or len(name) > 100:  # Limiter la longueur
        return False
    
    # Exclure les patterns qui ne sont pas des noms d'items
    exclude_patterns = [
        r'^\d+$',  # Que des chiffres
        r'^(max|min|level|lvl)\s*:',  # Patterns techniques
        r'^(pa|pm|pdv|pv)\s*\d+',  # Stats
        r'maîtrise|résistance',  # Stats
        r'abandon|accumulation|acribie',  # Noms de passifs
        r'webkit|keyframes|mui|css',  # CSS et JavaScript
        r'animation|transition|opacity',  # CSS
        r'font|color|padding|margin',  # CSS
        r'const|var|function|return',  # JavaScript
        r'wakfu.*mmorpg|ankama',  # Textes du site
        r'^build\d*$',  # "Build" seul
        r'retour\s+pa|brûlure|carapace|influence|poids\s+plume',  # Passifs
        r'agilité\s+vitale|force\s+vitale|maniement',  # Passifs
        r'fr_fr|locale|user',  # Variables
        r'^[a-z_-]+\s*:\s*',  # CSS properties
        r'\{|\}|\[|\]',  # Symboles de code
    ]
    
    name_lower = name.lower()
    for pattern in exclude_patterns:
        if re.search(pattern, name_lower):
            return False
    
    # Patterns positifs pour les vrais noms d'items
    positive_patterns = [
        r'\b(cape|casque|heaume|épée|dague|anneau|amulette|bottes|ceinture|armure|cuirasse)\b',
        r'\b(ring|helmet|sword|cape|boots|armor|shield|dagger|amulet)\b',
        r'\b(légendaire|épique|rare|mythique|relique)\b',
    ]
    
    # Si un pattern positif matche, accepter
    for pattern in positive_patterns:
        if re.search(pattern, name_lower):
            return True
    
    # Sinon, vérifier que ce n'est pas trop technique
    if re.search(r'^[A-Z][a-zA-ZÀ-ÿ\s\-\']+$', name):  # Format nom propre
        return True
    
    return False

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python zenith_tooltip_extractor.py <BUILD_URL>")
        sys.exit(1)
    
    url = sys.argv[1]
    items = asyncio.run(extract_items_from_tooltips(url))
    
    print(f"\n✅ {len(items)} équipements extraits:")
    for item in items:
        print(f"  - {item['name']} [{item['rarity']}]")