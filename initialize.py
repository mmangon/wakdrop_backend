#!/usr/bin/env python3
"""
Script d'initialisation complet pour WakDrop Backend

Ce script:
1. Crée les tables de la base de données
2. Synchronise les données du CDN Wakfu (items, recettes, etc.)
3. Lance un scraping initial des monstres et leurs drops
4. Génère un rapport d'initialisation

Usage:
    python initialize.py [--pages N] [--headless]
"""

import asyncio
import argparse
import time
import json
from datetime import datetime
from typing import Dict, Any
import logging

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def create_database_tables():
    """Crée toutes les tables de la base de données"""
    logger.info("📊 Création des tables de la base de données...")
    
    try:
        from core.database import engine, Base
        from models import build, cache  # Import pour charger les modèles
        
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Tables créées avec succès")
        return True
    except Exception as e:
        logger.error(f"❌ Erreur création tables: {e}")
        return False

async def sync_cdn_data():
    """Synchronise les données depuis le CDN Wakfu"""
    logger.info("🌐 Synchronisation des données CDN...")
    
    try:
        from services.wakfu_cdn import wakfu_cdn
        from services.analysis import analysis_service
        
        # Récupérer la version actuelle
        version = await wakfu_cdn.get_current_version()
        logger.info(f"📌 Version CDN: {version}")
        
        # Récupérer les données
        logger.info("📥 Récupération des items...")
        items = await wakfu_cdn.get_items()
        
        logger.info("📥 Récupération des recettes...")
        recipes = await wakfu_cdn.get_recipes()
        
        logger.info("📥 Récupération des loots de récolte...")
        harvest_loots = await wakfu_cdn.get_harvest_loots()
        
        if items:
            logger.info(f"📦 {len(items)} items récupérés")
            
            # Analyser et mettre en cache
            await analysis_service.update_items_cache(
                items=items or [],
                recipes=recipes or [],
                harvest_loots=harvest_loots or []
            )
            
            logger.info("✅ Données CDN synchronisées et analysées")
            return {
                'version': version,
                'items_count': len(items) if items else 0,
                'recipes_count': len(recipes) if recipes else 0,
                'harvest_loots_count': len(harvest_loots) if harvest_loots else 0
            }
        else:
            logger.warning("⚠️ Aucun item récupéré depuis le CDN")
            return None
            
    except Exception as e:
        logger.error(f"❌ Erreur synchronisation CDN: {e}")
        return None
    finally:
        if 'wakfu_cdn' in locals():
            await wakfu_cdn.close()

async def scrape_initial_monsters(pages: int = 5, headless: bool = True):
    """
    Lance un scraping initial des monstres et leurs drops
    
    Args:
        pages: Nombre de pages à scraper (environ 20 monstres par page)
        headless: Si True, Chrome s'exécute en arrière-plan
    """
    logger.info(f"🕷️ Démarrage du scraping ({pages} pages)...")
    logger.info("⏱️ Cela peut prendre du temps (environ 2-3 min par page)")
    
    try:
        # from services.selenium_scraper import WakfuSeleniumScraper  # Module supprimé
        
        scraper = WakfuSeleniumScraper(headless=headless, page_delay=2.0)
        
        # Scraper les monstres
        start_time = time.time()
        monsters = scraper.scrape_all_monsters(start_page=1, end_page=pages)
        elapsed = time.time() - start_time
        
        logger.info(f"⏱️ Scraping terminé en {elapsed/60:.1f} minutes")
        logger.info(f"📊 {len(monsters)} monstres récupérés")
        
        # Sauvegarder les données brutes
        with open('monsters_init.json', 'w', encoding='utf-8') as f:
            json.dump(monsters, f, ensure_ascii=False, indent=2)
        logger.info("💾 Données sauvegardées dans monsters_init.json")
        
        # Importer en base de données
        logger.info("📤 Import en base de données...")
        results = scraper.import_to_database(monsters)
        
        logger.info(f"""
        ✅ Import terminé:
        - Monstres ajoutés: {results['monsters_added']}
        - Drops ajoutés: {results['drops_added']}
        - Drops mis à jour: {results['drops_updated']}
        - Erreurs: {len(results.get('errors', []))}
        """)
        
        scraper.close()
        return results
        
    except Exception as e:
        logger.error(f"❌ Erreur scraping: {e}")
        return None

async def test_api_endpoints():
    """Test rapide des endpoints principaux"""
    logger.info("🔍 Test des endpoints API...")
    
    try:
        import httpx
        
        async with httpx.AsyncClient() as client:
            # Test endpoint racine
            response = await client.get("http://localhost:8000/")
            if response.status_code == 200:
                logger.info("✅ API accessible")
                
            # Test stats des drops
            response = await client.get("http://localhost:8000/drops/stats")
            if response.status_code == 200:
                stats = response.json()
                logger.info(f"📊 Stats: {stats.get('total_drops')} drops en base")
                return stats
            
    except Exception as e:
        logger.warning(f"⚠️ API non accessible (normal si pas lancée): {e}")
        return None

async def generate_init_report(results: Dict[str, Any]):
    """Génère un rapport d'initialisation"""
    report = {
        'timestamp': datetime.now().isoformat(),
        'database': results.get('database', False),
        'cdn_sync': results.get('cdn_sync'),
        'scraping': results.get('scraping'),
        'api_test': results.get('api_test')
    }
    
    # Sauvegarder le rapport
    with open('init_report.json', 'w') as f:
        json.dump(report, f, indent=2)
    
    logger.info("""
    ═══════════════════════════════════════════
    🎉 INITIALISATION TERMINÉE !
    ═══════════════════════════════════════════
    
    Prochaines étapes:
    1. Lancer l'API: python main.py
    2. Accéder à la documentation: http://localhost:8000/docs
    3. Le frontend Vue.js peut maintenant utiliser l'API
    
    Endpoints principaux:
    - POST /builds/ : Parser un build Zenith
    - GET /builds/{id}/roadmap : Obtenir la roadmap de farm
    - POST /drops/scrape : Lancer plus de scraping si besoin
    - GET /drops/stats : Voir les statistiques
    
    Rapport sauvegardé dans: init_report.json
    ═══════════════════════════════════════════
    """)

async def main():
    """Fonction principale d'initialisation"""
    parser = argparse.ArgumentParser(description='Initialisation WakDrop Backend')
    parser.add_argument(
        '--pages', 
        type=int, 
        default=5,
        help='Nombre de pages de monstres à scraper (défaut: 5, ~100 monstres)'
    )
    parser.add_argument(
        '--headless',
        action='store_true',
        help='Exécuter Chrome en mode headless (sans interface)'
    )
    parser.add_argument(
        '--skip-scraping',
        action='store_true',
        help='Ignorer le scraping (utiliser si déjà fait)'
    )
    
    args = parser.parse_args()
    
    logger.info("""
    ╔════════════════════════════════════════╗
    ║     WakDrop Backend - Initialisation   ║
    ╚════════════════════════════════════════╝
    """)
    
    results = {}
    
    # 1. Créer les tables
    results['database'] = await create_database_tables()
    if not results['database']:
        logger.error("Impossible de continuer sans base de données")
        return
    
    # 2. Synchroniser le CDN
    results['cdn_sync'] = await sync_cdn_data()
    
    # 3. Scraper les monstres (optionnel)
    if not args.skip_scraping:
        results['scraping'] = await scrape_initial_monsters(
            pages=args.pages,
            headless=args.headless
        )
    else:
        logger.info("⏭️ Scraping ignoré (--skip-scraping)")
    
    # 4. Tester l'API
    results['api_test'] = await test_api_endpoints()
    
    # 5. Générer le rapport
    await generate_init_report(results)

if __name__ == "__main__":
    asyncio.run(main())