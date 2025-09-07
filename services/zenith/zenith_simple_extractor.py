#!/usr/bin/env python3
"""
Extracteur ZenithWakfu simplifié
Extraction directe du nom et de la rareté depuis les tooltips
"""

import asyncio
import re
import sys
from typing import List, Dict
from playwright.async_api import async_playwright

async def extract_items_simple(build_url: str) -> List[Dict[str, str]]:
    """
    Extraction simple et directe des items
    Se concentre uniquement sur nom + rareté
    """
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=True)
    page = await browser.new_page()
    
    try:
        # Navigation optimisée
        await page.goto(build_url, wait_until='domcontentloaded')
        
        # Gérer le modal GDPR (plus rapide)
        try:
            refuse_btn = await page.wait_for_selector('button:has-text("Ne pas consentir")', timeout=1000)
            if refuse_btn:
                await refuse_btn.click()
                await page.wait_for_timeout(200)
        except:
            pass
        
        # Attendre que les images d'items soient chargées
        await page.wait_for_selector('img[src*="/items/"]', timeout=5000)
        await page.wait_for_timeout(1000)  # Temps minimal pour stabilité
        
        # Stratégie différente : survoler une image à la fois et extraire immédiatement
        img_elements = await page.query_selector_all('img[src*="/items/"]')
        print(f"DEBUG: Survol séquentiel de {len(img_elements)} images d'items", file=sys.stderr)
        
        items = []
        processed_names = set()  # Noms d'items déjà traités
        processed_images = set()  # URLs d'images déjà traitées
        max_slots = 15  # Maximum d'emplacements d'équipement dans Wakfu
        
        for i, img in enumerate(img_elements):
            # Sortie rapide si on a déjà tous les slots possibles
            if len(items) >= max_slots:
                print(f"DEBUG: Limite de {max_slots} items atteinte, arrêt anticipé", file=sys.stderr)
                break
            try:
                # Vérifier si cette image n'a pas déjà été traitée
                img_src = await img.get_attribute('src')
                if img_src in processed_images:
                    continue
                    
                # Survoler l'image (plus rapide)
                await img.hover()
                await page.wait_for_timeout(200)  # Réduit de 500ms à 200ms
                
                # Chercher le tooltip qui vient d'apparaître
                tooltip_elements = await page.query_selector_all('.tooltip-main-block, [class*="tooltip"]')
                
                for elem in tooltip_elements:
                    try:
                        # Vérifier si l'élément est visible
                        is_visible = await elem.is_visible()
                        if not is_visible:
                            continue
                            
                        # Extraire les informations  
                        inner_html = await elem.inner_html()
                        rarity = extract_rarity_from_html(inner_html)
                        
                        # Chercher le nom
                        name = None
                        title_elem = None
                        
                        # 1. Chercher dans .tooltip-title
                        title_elem = await elem.query_selector('.tooltip-title, [class*="tooltip-title"]')
                        if title_elem:
                            name = await title_elem.text_content()
                            # Si pas de rareté trouvée sur le conteneur, chercher sur le titre
                            if rarity == 'unknown':
                                title_class = await title_elem.get_attribute('class') or ''
                                rarity = extract_rarity_from_classes(title_class)
                        
                        # 2. Si pas trouvé, chercher dans le texte général
                        if not name:
                            text = await elem.text_content()
                            if text:
                                lines = [line.strip() for line in text.split('\n') if line.strip()]
                                if lines:
                                    name = lines[0]
                        
                        # Nettoyer et valider
                        if name:
                            name = clean_item_name(name)
                            if len(name) > 3 and is_valid_item_name(name) and name not in processed_names:
                                processed_names.add(name)
                                processed_images.add(img_src)
                                items.append({
                                    'name': name,
                                    'rarity': rarity
                                })
                                print(f"DEBUG: Item {i+1} trouvé -> {name} [{rarity}]", file=sys.stderr)
                                break  # Sortir de la boucle tooltip une fois qu'on a trouvé l'item
                        
                    except Exception as e:
                        continue
                
                # Pause réduite entre les survols
                await page.wait_for_timeout(50)
                
            except:
                continue
        
        print(f"DEBUG: {len(items)} items uniques extraits", file=sys.stderr)
        return items
        
    finally:
        await browser.close()
        await playwright.stop()

def extract_rarity_from_html(html: str) -> str:
    """Extrait la rareté depuis le HTML du tooltip"""
    if not html:
        return 'unknown'
        
    html_lower = html.lower()
    
    # Patterns spécifiques à ZenithWakfu dans le HTML
    # Chercher dans l'ordre de priorité (plus rare en premier)
    rarity_patterns = [
        ('relic', ['relic', 'relique']),
        ('mythic', ['mythic', 'mythique']), 
        ('legendary', ['legendary', 'légendaire']),
        ('epic', ['epic', 'épique']),
        ('rare', ['rare']),
        ('unusual', ['unusual', 'inhabituel']),
        ('common', ['common', 'commun'])
    ]
    
    for rarity_name, patterns in rarity_patterns:
        for pattern in patterns:
            # Chercher dans les classes, styles, ou text
            if (f'rarity-{pattern}' in html_lower or
                f'{pattern}-rarity' in html_lower or
                f'{pattern}-item' in html_lower or
                f'class="{pattern}' in html_lower or
                f"class='{pattern}" in html_lower or
                f'rarity{pattern}' in html_lower):
                return rarity_name
    
    return 'unknown'

def extract_rarity_from_classes(class_str: str) -> str:
    """Extrait la rareté depuis les classes CSS (fonction dépréciée)"""
    return extract_rarity_from_html(class_str)

def clean_item_name(name: str) -> str:
    """Nettoie le nom d'un item"""
    if not name:
        return ''
    
    # Retirer les patterns indésirables
    name = re.sub(r'^\d+\s*', '', name)  # Chiffres en début
    name = re.sub(r'Niv\.\s*\d+', '', name)  # "Niv. XX"
    name = re.sub(r'\s+', ' ', name)  # Espaces multiples
    name = name.strip()
    
    return name

def is_valid_item_name(name: str) -> bool:
    """Vérifie si c'est un nom d'item valide"""
    if not name or len(name) < 4 or len(name) > 50:
        return False
    
    # Exclure les patterns non-items
    exclude_patterns = [
        r'^(pa|pm|pdv|pv)\s*\d+',  # Stats
        r'webkit|css|mui',  # CSS
        r'retour\s+pa|brûlure|carapace',  # Passifs
        r'^build$',  # "Build" seul
    ]
    
    name_lower = name.lower()
    for pattern in exclude_patterns:
        if re.search(pattern, name_lower):
            return False
    
    return True

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python zenith_simple_extractor.py <BUILD_URL>")
        sys.exit(1)
    
    url = sys.argv[1]
    items = asyncio.run(extract_items_simple(url))
    
    print(f"\n✅ {len(items)} équipements extraits:")
    for item in items:
        print(f"  - {item['name']} [{item['rarity']}]")