import httpx
import re
from typing import List, Optional, Dict
from urllib.parse import urlparse

class ZenithService:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
    
    def extract_build_id(self, zenith_url: str) -> Optional[str]:
        """Extrait l'ID du build depuis l'URL Zenith"""
        # URL format: https://www.zenithwakfu.com/builder/v3dhe
        path = urlparse(zenith_url).path
        build_id = path.split('/')[-1] if path else None
        return build_id if build_id else None
    
    async def fetch_build_data(self, zenith_url: str) -> Optional[Dict]:
        """Récupère les données d'un build Zenith"""
        try:
            response = await self.client.get(zenith_url)
            response.raise_for_status()
            html_content = response.text
            
            # Cherche les données JavaScript du build
            # Pattern typique: window.buildData = {...}
            build_pattern = r'window\.buildData\s*=\s*(\{.*?\});'
            match = re.search(build_pattern, html_content, re.DOTALL)
            
            if match:
                import json
                build_data = json.loads(match.group(1))
                return build_data
            
            # Fallback: cherche d'autres patterns possibles
            # Peut nécessiter ajustement selon la vraie structure Zenith
            return None
            
        except Exception as e:
            print(f"Erreur fetch build {zenith_url}: {e}")
            return None
    
    def extract_equipped_items(self, build_data: Dict) -> List[int]:
        """Extrait les IDs des items équipés depuis les données du build"""
        items = []
        
        # Structure supposée du build Zenith (à ajuster selon la vraie API)
        if "equipment" in build_data:
            equipment = build_data["equipment"]
            
            # Slots d'équipement standards Wakfu
            slots = [
                "helmet", "shoulders", "amulet", "breastplate", 
                "leftRing", "rightRing", "belt", "boots", "cape",
                "weapon", "secondHand"
            ]
            
            for slot in slots:
                if slot in equipment and equipment[slot]:
                    item_id = equipment[slot].get("id")
                    if item_id:
                        items.append(item_id)
        
        return items
    
    async def parse_build(self, zenith_url: str) -> Optional[Dict]:
        """Parse complet d'un build Zenith"""
        build_id = self.extract_build_id(zenith_url)
        if not build_id:
            return None
        
        build_data = await self.fetch_build_data(zenith_url)
        if not build_data:
            return None
        
        equipped_items = self.extract_equipped_items(build_data)
        
        return {
            "zenith_id": build_id,
            "zenith_url": zenith_url,
            "items_ids": equipped_items,
            "raw_data": build_data
        }
    
    async def close(self):
        """Ferme le client HTTP"""
        await self.client.aclose()

zenith_service = ZenithService()