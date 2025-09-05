import httpx
import json
from typing import Dict, List, Optional
from core.config import settings

class WakfuCDNService:
    def __init__(self):
        self.base_url = settings.wakfu_cdn_base_url
        self.version = settings.wakfu_version
        self.client = httpx.AsyncClient(timeout=60.0)
    
    async def get_current_version(self) -> str:
        """Récupère la version actuelle depuis config.json"""
        try:
            response = await self.client.get(f"{self.base_url}/config.json")
            response.raise_for_status()
            config = response.json()
            return config.get("version", self.version)
        except Exception as e:
            print(f"Erreur récupération version: {e}")
            return self.version
    
    async def fetch_data_type(self, data_type: str) -> Optional[Dict]:
        """Récupère un type de données du CDN"""
        try:
            url = f"{self.base_url}/{self.version}/{data_type}.json"
            response = await self.client.get(url)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Erreur fetch {data_type}: {e}")
            return None
    
    async def get_items(self) -> Optional[List[Dict]]:
        """Récupère tous les items"""
        return await self.fetch_data_type("items")
    
    async def get_recipes(self) -> Optional[List[Dict]]:
        """Récupère toutes les recettes"""
        return await self.fetch_data_type("recipes")
    
    async def get_recipe_ingredients(self) -> Optional[List[Dict]]:
        """Récupère les ingrédients des recettes"""
        return await self.fetch_data_type("recipeIngredients")
    
    async def get_harvest_loots(self) -> Optional[List[Dict]]:
        """Récupère les loots de récolte"""
        return await self.fetch_data_type("harvestLoots")
    
    async def get_item_properties(self) -> Optional[List[Dict]]:
        """Récupère les propriétés des items"""
        return await self.fetch_data_type("itemProperties")
    
    def analyze_item_obtention(self, item: Dict, recipes: List[Dict], harvest_loots: List[Dict]) -> str:
        """Analyse comment obtenir un item"""
        item_id = item.get("definition", {}).get("item", {}).get("id")
        
        # Check si c'est dans les propriétés spéciales
        properties = item.get("definition", {}).get("item", {}).get("properties", [])
        if 7 in properties:  # Shop
            return "shop"
        if 1 in properties:  # Trésor
            return "treasure"
        
        # Check si craftable
        for recipe in recipes:
            if recipe.get("resultId") == item_id:
                return "craft"
        
        # Check si droppable/récoltable
        for loot in harvest_loots:
            if loot.get("itemId") == item_id:
                return "harvest"
        
        # Par défaut
        return "unknown"
    
    async def close(self):
        """Ferme le client HTTP"""
        await self.client.aclose()

wakfu_cdn = WakfuCDNService()