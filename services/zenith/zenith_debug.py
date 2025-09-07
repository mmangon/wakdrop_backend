#!/usr/bin/env python3
"""
Script de debug pour analyser la structure HTML de ZenithWakfu
"""

import asyncio
from playwright.async_api import async_playwright

async def debug_zenith_page(url: str):
    """Capture et analyse la structure de la page"""
    
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=True)
    page = await browser.new_page()
    
    try:
        print(f"Navigation vers: {url}")
        await page.goto(url, wait_until='networkidle', timeout=30000)
        
        # Attendre un peu pour que tout se charge
        await page.wait_for_timeout(5000)
        
        # Capturer le HTML pour debug
        print("\n=== Recherche d'éléments avec images ===")
        
        # Chercher toutes les images
        images = await page.query_selector_all('img')
        print(f"Nombre total d'images: {len(images)}")
        
        # Analyser les premières images
        for i, img in enumerate(images[:10]):
            src = await img.get_attribute('src')
            parent_class = await img.evaluate('(el) => el.parentElement.className')
            parent_aria = await img.evaluate('(el) => el.parentElement.getAttribute("aria-describedby")')
            print(f"\nImage {i+1}:")
            print(f"  src: {src}")
            print(f"  parent class: {parent_class}")
            print(f"  parent aria-describedby: {parent_aria}")
        
        # Chercher spécifiquement les éléments avec aria-describedby
        print("\n=== Éléments avec aria-describedby ===")
        aria_elements = await page.query_selector_all('[aria-describedby]')
        print(f"Nombre d'éléments avec aria-describedby: {len(aria_elements)}")
        
        for i, elem in enumerate(aria_elements[:5]):
            tag = await elem.evaluate('(el) => el.tagName')
            aria_value = await elem.get_attribute('aria-describedby')
            has_img = await elem.query_selector('img')
            print(f"\nElement {i+1}:")
            print(f"  tag: {tag}")
            print(f"  aria-describedby: {aria_value}")
            print(f"  contient image: {has_img is not None}")
        
        # Sauvegarder le HTML complet pour analyse
        html = await page.content()
        with open('zenith_page.html', 'w', encoding='utf-8') as f:
            f.write(html)
        print("\n✅ HTML sauvegardé dans zenith_page.html")
        
        # Prendre une capture d'écran
        await page.screenshot(path='zenith_screenshot.png', full_page=True)
        print("📸 Screenshot sauvegardé dans zenith_screenshot.png")
        
    finally:
        await browser.close()
        await playwright.stop()

if __name__ == "__main__":
    url = "https://www.zenithwakfu.com/builder/henpz"
    asyncio.run(debug_zenith_page(url))