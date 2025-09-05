# WakDrop Backend - API FastAPI

## 🎯 Objectif Principal
Application pour créer des builds Wakfu et générer des **roadmaps de farm détaillées** indiquant:
- **Quels monstres** farmer pour obtenir les items
- Dans **quelles zones** trouver ces monstres
- Les **taux de drop** précis pour optimiser le farm

## 🏗️ Architecture Globale
- **Backend** (ce projet) : API REST FastAPI + PostgreSQL
  - **Recherche intelligente d'items par texte** 🔍
  - Gère les données d'items et de drop
  - Génère les roadmaps de farm optimisées
  - Expose l'API REST pour le frontend
  
- **Frontend** (projet séparé: `wakdropfrontend`) : Application Vue.js
  - Interface utilisateur simple et intuitive
  - **Saisie d'items en texte libre** : "Épée Iop, Cape du Feu"
  - Affichage des roadmaps interactives
  - Visualisation des zones de farm

## ⚙️ Stack Technique
- **Framework** : FastAPI 0.104.1
- **Database** : PostgreSQL + SQLAlchemy
- **HTTP Client** : httpx (pour CDN)
- **Python** : 3.9+
- **Recherche** : Système de recherche intelligent avec scoring de pertinence

## 🏗️ Architecture
```
wakdrop_backend/
├── models/          # SQLAlchemy models
│   ├── build.py     # Builds utilisateur
│   └── cache.py     # Cache items CDN + données de drop
├── services/        
│   ├── wakfu_cdn.py # Sync CDN Wakfu + analyse obtention
│   ├── drop_manager.py # Génération roadmaps farm optimisées
│   └── analysis.py  # Services d'analyse 
├── routers/         # Endpoints FastAPI
│   ├── builds.py    # CRUD builds
│   ├── search.py    # 🔍 Recherche d'items + création builds depuis texte
│   ├── items.py     # Détails items 
│   ├── drops.py     # Données de drop des monstres
│   ├── cdn.py       # Sync CDN
│   └── admin.py     # Initialisation système
├── core/            # Config, DB, dependencies
├── main.py          # App FastAPI
└── API_DOCUMENTATION.md # 📚 Doc complète pour le frontend
```

## 📡 Sources de Données

### CDN Wakfu Officiel
- **URL** : `https://wakfu.cdn.ankama.com/gamedata/{version}/`
- **Version actuelle** : 1.88.1.39 (via config.json)

### Endpoints CDN disponibles:
- `actions.json` - Descriptions des types d'effets (perte PdV, boost PA, etc)
- `items.json` - Équipements, stats, effets (~20Mo, 8230+ items)
- `jobsItems.json` - Version light des items (récoltés, craftés, utilisés)
- `recipes.json` - Liste des recettes
- `recipeIngredients.json` - Ingrédients des crafts
- `recipeResults.json` - Objets produits par les crafts
- `recipeCategories.json` - Liste des métiers
- `harvestLoots.json` - Objets récupérés via la récolte
- `collectibleResources.json` - Actions de récolte
- `itemProperties.json` - Propriétés des objets
- `equipmentItemTypes.json` - Types d'équipements et emplacements
- `states.json` - Traductions des états

### Propriétés items (itemProperties):
- 1 : Objet trésor (interface spéciale)
- 7 : Objet shop (boutique uniquement)
- 8 : Relique (un seul équipable)
- 12 : Épique (un seul équipable)
- 13 : Non recyclable
- 19 : Emplacement gemme épique
- 20 : Emplacement gemme relique

⚠️ **IMPORTANT**: Le CDN ne fournit PAS les données de drop des monstres. Ces données ont été importées depuis des scripts de scraping externes.

## 🚀 Endpoints API

### 🔍 **Search** (Cœur du système - Recherche intelligente)
- `POST /search/items` - **⭐ Recherche d'items par texte libre**
- `POST /search/build-from-text` - **🔥 Créer un build depuis du texte : "Épée Iop, Cape du Feu"**

### 🎮 Builds (Gestion des builds)
- `POST /builds/` - Crée un build depuis une liste d'items
- `GET /builds/{id}` - Récupère les détails d'un build
- `GET /builds/{id}/roadmap` - **🔥 Génère la roadmap de farm complète**
- `POST /builds/{id}/analyze` - Analyse complète avec données de drop

### 📦 Items (Gestion des items)  
- `GET /items/{id}` - Détails d'un item depuis le cache
- `GET /items/{id}/obtention` - Infos d'obtention (craft, shop, etc.)

### 🌐 CDN (Synchronisation Wakfu)
- `POST /cdn/sync` - Lance la sync des données CDN en arrière-plan
- `GET /cdn/version` - Version actuelle du CDN
- `GET /cdn/stats` - Statistiques du cache

### 👾 Drops (Données de farm)
- `GET /drops/item/{item_id}` - Tous les monstres qui drop un item
- `GET /drops/monster/{monster_id}` - Tous les items d'un monstre
- `POST /drops/farm-roadmap` - **🔥 Roadmap pour une liste d'items**
- `POST /drops/import` - **🆕 Import de données depuis script externe**
- `GET /drops/stats` - Statistiques des drops en base
- `DELETE /drops/clear` - ⚠️ Supprime toutes les données de drop

### 🔧 Admin (Initialisation et maintenance)
- `POST /admin/initialize` - **🚀 Initialisation complète du système**
- `GET /admin/init-status` - Statut de l'initialisation en cours
- `POST /admin/quick-setup` - Setup rapide (CDN uniquement, sans scraping)
- `POST /admin/import-json` - Importe des données depuis un fichier JSON
- `GET /admin/system-info` - Informations système et statistiques

## 📦 Modèles de Données

### Build
```python
id: int
zenith_url: str
zenith_id: str  
items_ids: List[int]
created_at: datetime
```

### CachedItem
```python
id: int
wakfu_id: int
data_json: dict         # Données brutes CDN
obtention_type: str     # "craft|harvest|shop|treasure|unknown"
last_updated: datetime
```

### FarmAnalysis
```python
build_id: int
item_id: int
obtention_type: str
farm_data: dict        # Infos spécifiques farm
```

## 🔄 Workflow Utilisateur Final

### ✨ **Méthode Principale : Recherche par Texte**
1. **Utilisateur** saisit : `"Épée Iop niveau 200, Cape du feu, Anneau PA"`
2. **API** (`/search/build-from-text`) :
   - Recherche automatiquement les items correspondants
   - Calcule les scores de pertinence  
   - Trouve les monstres qui drop ces items
3. **Génère roadmap optimisée** :
   - Priorité des monstres par nombre d'items
   - Zones de farm avec taux de drop
   - Temps estimé de farm
4. **Utilisateur** reçoit sa roadmap complète

### 🔧 **Méthode Avancée : Recherche Item par Item**
1. **Utilisateur** tape : `"épée"`
2. **API** retourne toutes les épées avec scores
3. **Utilisateur** sélectionne les items précis
4. **Génère roadmap** sur mesure

### 📊 **Architecture des Données**
1. **✅ CDN Wakfu** → 8,230+ items synchronisés
2. **✅ Données de drop** → 604 monstres avec 10,517+ drops  
3. **✅ Algorithme de priorisation** → Optimise les zones de farm
4. **✅ API REST** → Interface simple pour le frontend

## ⚙️ Configuration

### Variables d'environnement (.env)
```bash
DATABASE_URL=postgresql://user:pass@localhost:5432/wakdrop
WAKFU_CDN_BASE_URL=https://wakfu.cdn.ankama.com/gamedata
WAKFU_VERSION=1.88.1.39
```

## 🚀 Installation & Lancement

### 1️⃣ Installation des dépendances
```bash
# Créer l'environnement virtuel
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows

# Installer les packages
pip install -r requirements.txt
pip install pydantic-settings  # Si pas dans requirements.txt

# Configuration
cp .env.example .env
# Éditer .env avec vos paramètres PostgreSQL
```

### 2️⃣ Initialisation (PREMIÈRE FOIS)
```bash
# Méthode 1: Script d'initialisation complet
python initialize.py --pages 5 --headless

# Méthode 2: Via l'API
python main.py  # Lancer l'API d'abord
# Puis dans un autre terminal:
curl -X POST http://localhost:8000/admin/initialize \
  -H "Content-Type: application/json" \
  -d '{"scrape_pages": 5, "headless": true}'
```

### 3️⃣ Lancement de l'API
```bash
# Développement (avec auto-reload)
python main.py
# ou
uvicorn main:app --reload --port 8000

# Production
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4

# Accès
# API: http://localhost:8000
# Documentation interactive: http://localhost:8000/docs
```

## 📋 Commandes Utiles
- `uvicorn main:app --reload` - Serveur dev avec auto-reload
- `python -c "from core.database import engine, Base; Base.metadata.create_all(engine)"` - Créer tables

## 📊 État actuel du système

### ✅ **Système Complet et Fonctionnel**
- **🔍 Recherche intelligente d'items par texte** avec scoring de pertinence
- **🎯 Création de builds depuis texte libre** : "Épée Iop, Cape du Feu"
- **📊 8,230+ items** synchronisés depuis le CDN Wakfu
- **👾 604 monstres** avec 10,517+ données de drop importées
- **🗺️ Génération automatique de roadmaps** de farm optimisées
- **📚 Documentation API complète** pour le frontend
- **🔗 CORS configuré** pour Vue.js
- **⚡ API REST rapide** avec FastAPI + PostgreSQL

### 🚀 **Prêt pour le Frontend**
- **Endpoint principal** : `POST /search/build-from-text`
- **Interface simple** : L'utilisateur tape du texte libre
- **Résultat immédiat** : Roadmap complète avec zones de farm
- **Documentation** : Voir `API_DOCUMENTATION.md`

### 🔧 **Améliorations Futures (Optionnelles)**
- [ ] Cache Redis pour performances
- [ ] Pagination pour résultats volumineux  
- [ ] Tests unitaires complets
- [ ] Docker et docker-compose
- [ ] Rate limiting et authentification
- [ ] Interface d'administration web

## 🌐 Déploiement
- **Serveur** : LXC avec PostgreSQL
- **Proxy** : Nginx reverse proxy
- **SSL** : Let's Encrypt