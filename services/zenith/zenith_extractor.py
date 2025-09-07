#!/usr/bin/env python3
"""
Extracteur d'items depuis ZenithWakfu
Capture les données des tooltips MUI qui apparaissent au survol des items
"""

import asyncio
import json
import re
from typing import Dict, List, Optional
from playwright.async_api import async_playwright, Page
import time

class ZenithExtractor:
    def __init__(self, headless: bool = False):
        self.headless = headless
        self.browser = None
        self.page = None
        self.playwright = None
        
    async def initialize(self):
        """Initialise le navigateur et la page"""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=['--no-sandbox', '--disable-setuid-sandbox']
        )
        context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        self.page = await context.new_page()
        
    async def navigate_to_build(self, build_url: str):
        """Navigue vers une page de build ZenithWakfu"""
        print(f"Navigation vers: {build_url}")
        await self.page.goto(build_url, wait_until='networkidle')
        await self.page.wait_for_timeout(3000)  # Attendre le chargement complet
        
        # Gérer le modal de consentement GDPR s'il apparaît
        try:
            # Chercher le bouton "Ne pas consentir" ou "Autoriser"
            consent_button = await self.page.wait_for_selector(
                'button:has-text("Ne pas consentir"), button:has-text("Autoriser")',
                timeout=5000
            )
            if consent_button:
                print("Modal de consentement détecté, fermeture...")
                # Cliquer sur "Ne pas consentir" pour fermer rapidement
                refuse_button = await self.page.query_selector('button:has-text("Ne pas consentir")')
                if refuse_button:
                    await refuse_button.click()
                else:
                    await consent_button.click()
                await self.page.wait_for_timeout(2000)  # Attendre que le modal se ferme
        except:
            # Pas de modal, continuer
            pass
        
    async def extract_item_tooltip_data(self, item_element) -> Optional[Dict]:
        """
        Extrait les données de la tooltip d'un item
        
        Args:
            item_element: Element à survoler
            
        Returns:
            Dictionnaire avec les données de l'item
        """
        try:
            # Survoler l'item pour déclencher la tooltip
            await item_element.hover()
            await self.page.wait_for_timeout(800)  # Attendre que la tooltip apparaisse
            
            # Chercher la tooltip MUI
            tooltip_selectors = [
                'div[class*="MuiTooltip-popper"]',
                'div[role="tooltip"]',
                'div[class*="MuiTooltip-tooltip"]',
                '.MuiTooltip-popper'
            ]
            
            tooltip = None
            for selector in tooltip_selectors:
                try:
                    tooltip = await self.page.wait_for_selector(selector, timeout=1000, state='visible')
                    if tooltip:
                        break
                except:
                    continue
            
            if not tooltip:
                print("Tooltip non trouvée")
                return None
            
            # Extraire le contenu complet
            text_content = await tooltip.inner_text()
            html_content = await tooltip.inner_html()
            
            # Parser les informations
            item_data = self.parse_item_from_text(text_content, html_content)
            
            # Ajouter le HTML brut pour référence
            item_data['raw_html'] = await tooltip.inner_html()
            
            # Sortir du survol
            await self.page.mouse.move(0, 0)
            await self.page.wait_for_timeout(200)
            
            return item_data
            
        except Exception as e:
            print(f"Erreur lors de l'extraction de la tooltip: {e}")
            return None
    
    def parse_item_from_text(self, text: str, html: str = None) -> Dict:
        """
        Parse le texte de la tooltip pour extraire les informations structurées
        
        Args:
            text: Texte de la tooltip
            html: HTML de la tooltip pour extraire plus d'infos
            
        Returns:
            Dictionnaire avec les infos parsées
        """
        lines = text.split('\n')
        item_data = {
            'name': '',
            'level': None,
            'rarity': None,
            'type': None,
            'stats': [],
            'raw_text': text
        }
        
        # Le nom est généralement sur la première ligne
        if lines:
            item_data['name'] = lines[0].strip()
        
        # Extraire la rareté depuis le HTML (dans les classes CSS)
        if html:
            # Classes de rareté dans ZenithWakfu
            rarity_mapping = {
                'legendary': 'Légendaire',
                'mythic': 'Mythique',
                'epic': 'Épique',
                'rare': 'Rare',
                'uncommon': 'Peu commun',
                'common': 'Commun'
            }
            
            for css_rarity, french_name in rarity_mapping.items():
                if f'rarity-{css_rarity}' in html or f'{css_rarity}-item' in html:
                    item_data['rarity'] = french_name
                    break
        
        # Parser le reste des lignes
        for line in lines[1:]:
            line = line.strip()
            if not line:
                continue
            
            # Niveau
            if 'Niveau' in line or 'Niv.' in line:
                level_match = re.search(r'(\d+)', line)
                if level_match:
                    item_data['level'] = int(level_match.group(1))
            
            # Type d'équipement (depuis l'icône dans le HTML si possible)
            if any(eq_type in line for eq_type in ['Casque', 'Plastron', 'Bottes', 'Ceinture', 'Épaulettes', 'Cape', 'Anneau', 'Amulette']):
                item_data['type'] = line
            
            # Stats (lignes avec +/- et chiffres)
            stat_match = re.match(r'([+-]?\d+%?)\s+(.+)', line)
            if stat_match:
                item_data['stats'].append({
                    'value': stat_match.group(1),
                    'stat': stat_match.group(2)
                })
        
        # Extraire le type depuis le HTML si pas trouvé
        if not item_data['type'] and html:
            type_mapping = {
                'helmet': 'Casque',
                'breastplate': 'Plastron',
                'boots': 'Bottes',
                'belt': 'Ceinture',
                'epaulettes': 'Épaulettes',
                'cloak': 'Cape',
                'ring': 'Anneau',
                'necklace': 'Amulette',
                'weapon': 'Arme',
                'shield': 'Bouclier',
                'pet': 'Familier'
            }
            
            for en_type, fr_type in type_mapping.items():
                if f'type_items/{en_type}' in html:
                    item_data['type'] = fr_type
                    break
        
        return item_data
    
    async def extract_all_items_from_build(self, build_url: str) -> Dict:
        """
        Extrait tous les items d'un build ZenithWakfu
        
        Args:
            build_url: URL du build
            
        Returns:
            Dictionnaire avec tous les items extraits et les métadonnées
        """
        await self.navigate_to_build(build_url)
        
        # Attendre que les items soient chargés
        await self.page.wait_for_timeout(2000)
        
        # Debug: capturer le HTML pour voir la structure
        print("Recherche des items dans la page...")
        
        # Les items sont des images dans la zone d'équipement
        # Chercher les images qui semblent être des items d'équipement
        selectors_to_try = [
            'img[src*="/items/"]',  # Images d'items
            'img[src*="static.ankama.com/wakfu/portal/game/item"]',  # Items Ankama
            'div.equipment-slot img',  # Slots d'équipement
            'div[class*="equipment"] img',  # Zone d'équipement
            'img[width="40"]',  # Taille typique des items
            'img[height="40"]',
            'div.flex img[src*=".png"]',  # Images PNG dans les flex
            'div.flex img[src*=".webp"]',  # Images WEBP dans les flex
            'img.item-icon',  # Icônes d'items
            'button img',  # Images dans des boutons
        ]
        
        items_elements = []
        for selector in selectors_to_try:
            try:
                elements = await self.page.query_selector_all(selector)
                if elements:
                    print(f"✓ Trouvé {len(elements)} éléments avec: {selector}")
                    # Vérifier si ce sont vraiment des items
                    valid_items = []
                    for elem in elements:
                        # Vérifier si l'élément contient une image ou semble être un item
                        has_img = await elem.query_selector('img')
                        is_img = await elem.evaluate('(el) => el.tagName === "IMG"')
                        if has_img or is_img:
                            valid_items.append(elem)
                    
                    if valid_items:
                        print(f"  → {len(valid_items)} semblent être des items valides")
                        items_elements = valid_items
                        break
            except Exception as e:
                print(f"  Erreur avec {selector}: {e}")
                continue
        
        print(f"Nombre d'items trouvés: {len(items_elements)}")
        
        # Extraire les données de chaque item
        extracted_items = []
        for i, item_element in enumerate(items_elements):
            print(f"Extraction item {i+1}/{len(items_elements)}...")
            
            # Vérifier si l'élément est visible et a une image
            is_visible = await item_element.is_visible()
            if not is_visible:
                continue
            
            # Extraire les données de la tooltip
            item_data = await self.extract_item_tooltip_data(item_element)
            
            if item_data:
                # Essayer d'obtenir l'emplacement de l'item
                try:
                    parent = await item_element.evaluate_handle('(el) => el.parentElement')
                    slot_info = await parent.evaluate('(el) => el.className || el.id || ""')
                    item_data['slot'] = slot_info
                except:
                    pass
                
                extracted_items.append(item_data)
                
                # Petite pause entre les items pour éviter la détection
                await self.page.wait_for_timeout(1500)
        
        # Extraire l'ID du build depuis l'URL
        build_id = None
        if '/builder/' in build_url:
            build_id = build_url.split('/builder/')[-1].split('?')[0]
        
        return {
            'build_url': build_url,
            'build_id': build_id,
            'items_count': len(extracted_items),
            'items': extracted_items,
            'extraction_time': time.strftime('%Y-%m-%d %H:%M:%S')
        }
    
    async def close(self):
        """Ferme le navigateur"""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

async def test_extraction(build_url: str = None):
    """
    Fonction de test pour l'extraction ZenithWakfu
    
    Args:
        build_url: URL du build à extraire (optionnel)
    """
    
    if not build_url:
        # URL de test par défaut - à remplacer par une vraie URL
        build_url = input("Entrez l'URL du build ZenithWakfu: ").strip()
        if not build_url:
            print("URL requise!")
            return
    
    extractor = ZenithExtractor(headless=True)  # Mode headless pour serveur
    
    try:
        print("Initialisation du navigateur...")
        await extractor.initialize()
        
        print("Extraction des items du build...")
        build_data = await extractor.extract_all_items_from_build(build_url)
        
        # Sauvegarder les résultats
        filename = f'zenith_build_{build_data.get("build_id", "unknown")}.json'
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(build_data, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ Extraction terminée!")
        print(f"📊 {build_data['items_count']} items extraits")
        print(f"💾 Résultats sauvegardés dans {filename}")
        
        # Afficher un résumé
        print("\n📋 Résumé des items extraits:")
        for i, item in enumerate(build_data['items'], 1):
            name = item.get('name', 'Unknown')
            level = item.get('level', '?')
            stats_count = len(item.get('stats', []))
            print(f"  {i}. {name} (Niv. {level}) - {stats_count} stats")
        
        return build_data
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        raise
    finally:
        await extractor.close()

if __name__ == "__main__":
    # Installer playwright si nécessaire:
    # pip install playwright && playwright install chromium
    
    import sys
    
    build_url = sys.argv[1] if len(sys.argv) > 1 else None
    asyncio.run(test_extraction(build_url))