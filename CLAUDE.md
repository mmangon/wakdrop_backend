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
│   ├── cache.py     # Cache items CDN + données de drop
│   └── zones.py     # Zones géographiques et associations monstres
├── services/        
│   ├── wakfu_cdn.py # Sync CDN Wakfu + analyse obtention
│   ├── drop_manager.py # Génération roadmaps farm optimisées
│   ├── analysis.py  # Services d'analyse
│   └── zenith/      # 🆕 Services d'extraction ZenithWakfu
│       ├── zenith_extractor.py      # Extraction complète avec tooltips
│       ├── zenith_fast_extractor.py # Extraction rapide nom + ID
│       ├── zenith_minimal_extractor.py # Ultra-rapide (IDs uniquement)
│       └── extract_zenith_subprocess.py # Subprocess pour API
├── routers/         # Endpoints FastAPI
│   ├── builds.py    # CRUD builds
│   ├── search.py    # 🔍 Recherche d'items + création builds depuis texte
│   ├── zenith.py    # 🆕 Import builds depuis ZenithWakfu
│   ├── items.py     # Détails items 
│   ├── drops.py     # Données de drop des monstres
│   ├── zones_admin.py # Administration des zones
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

### 🚀 ZenithWakfu - Extraction d'Items (NOUVEAU)

Le système peut désormais extraire directement les builds depuis **ZenithWakfu** !

**Fonctionnement** :
- **Playwright** navigue sur ZenithWakfu en mode headless
- **Gestion automatique** du modal de consentement GDPR  
- **Extraction des noms et raretés** depuis les tooltips HTML
- **Extraction des IDs Wakfu** depuis les images : `../images/items/ID.webp`  
- **Mapping automatique** avec la base de données locale
- **Mapping des raretés** ZenithWakfu vers français : `legendary` → `Légendaire`
- **Temps d'exécution** : ~10-15 secondes pour un build complet

**Architecture d'extraction** :
- `zenith_extractor.py` - Version complète avec tooltips et stats
- `zenith_fast_extractor.py` - Version rapide avec nom + ID
- `zenith_simple_extractor.py` - **Version utilisée** : Noms + raretés (ultra-rapide)  
- `zenith_minimal_extractor.py` - Version IDs uniquement (dépréciée)
- `extract_zenith_subprocess.py` - Interface subprocess pour l'API

**Les IDs extraits correspondent exactement aux IDs du CDN Ankama** ✅  
**Les raretés extraites sont correctement mappées vers le français** ✅

## 🚀 Endpoints API

### 🚀 **Zenith** (Nouveau - Import ZenithWakfu)
- `POST /zenith/import` - **🔥 NEW: Import direct depuis ZenithWakfu**
- `GET /zenith/import/{build_id}` - Récupère un build importé avec roadmap

### 🔍 **Search** (Cœur du système - Recherche intelligente)  
- `POST /search/items` - **⭐ Recherche d'items par texte libre**
- `POST /search/build-from-text` - **🔥 Créer un build depuis du texte : "Épée Iop, Cape du Feu"**

### 🎮 Builds (Gestion des builds)
- `POST /builds/` - Crée un build depuis une liste d'items
- `GET /builds/{id}` - **🔥 Récupère les détails d'un build AVEC roadmap complète** (nouveau!)
- `GET /builds/{id}/roadmap` - Génère uniquement la roadmap de farm (déprécié, utiliser `/builds/{id}`)
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

### 🚀 **Méthode Principale : Import ZenithWakfu** (NOUVEAU)
1. **Utilisateur** copie l'URL de son build : `https://www.zenithwakfu.com/builder/henpz`
2. **Frontend** appelle : `POST /zenith/import` avec l'URL
3. **API** extrait automatiquement :
   - Les IDs Wakfu de tous les items équipés (~10-15 secondes)
   - Mappe avec la base de données locale
   - Crée le build en base
   - Génère la roadmap complète
4. **Utilisateur** reçoit immédiatement :
   - Build créé avec `build_id`
   - Liste des items trouvés/manquants  
   - Roadmap de farm optimisée

### ✨ **Méthode Alternative : Recherche par Texte**
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

### 🔧 **Méthode Alternative : Build Existant**
1. **Utilisateur** fait : `GET /builds/{id}` 
2. **API** retourne **la même structure** que `/search/build-from-text` :
   - Détails du build (build_id, created_at)
   - Items trouvés avec leurs détails complets
   - Roadmap de farm optimisée intégrée
3. **Avantage** : Une seule requête au lieu de deux !

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

#### 🔧 **Mode Développement** (Terminal)
```bash
# Script de gestion simplifié
./wakdrop_backend.sh dev

# Ou manuellement
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

#### 🚀 **Mode Production** (Service Systemd)
```bash
# Installation du service (une seule fois)
./wakdrop_backend.sh install   # Configure systemd + propose de démarrer

# Gestion quotidienne du service
./wakdrop_backend.sh start     # Démarrer
./wakdrop_backend.sh stop      # Arrêter
./wakdrop_backend.sh restart   # Redémarrer
./wakdrop_backend.sh status    # Statut
./wakdrop_backend.sh logs      # Logs temps réel
./wakdrop_backend.sh test      # Test API
```

#### 📍 **Accès**
- **API** : http://localhost:8000
- **Documentation** : http://localhost:8000/docs
- **Health Check** : http://localhost:8000/health

## 📋 Commandes Utiles
- `uvicorn main:app --reload` - Serveur dev avec auto-reload
- `python -c "from core.database import engine, Base; Base.metadata.create_all(engine)"` - Créer tables

## 📊 État actuel du système

### ✅ **Système Complet et Fonctionnel**
- **🚀 Import direct depuis ZenithWakfu** avec extraction ultra-rapide (10-15s)
- **🎨 Raretés ZenithWakfu authentiques** : `Légendaire`, `Épique`, `Relique`, `Rare`
- **🔍 Recherche intelligente d'items par texte** avec scoring de pertinence
- **🎯 Création de builds depuis texte libre** : "Épée Iop, Cape du Feu"
- **📊 8,230+ items** synchronisés depuis le CDN Wakfu
- **👾 844 monstres** avec 12,635+ données de drop importées
- **🏛️ Interface d'administration des zones** avec association monstres/zones
- **🗺️ Génération automatique de roadmaps** de farm optimisées avec zones
- **🆕 Endpoint `/builds/{id}` unifié** avec roadmap complète intégrée
- **📚 Documentation API complète** pour le frontend (v0.5.0)
- **🔗 CORS configuré** pour Vue.js
- **⚡ API REST rapide** avec FastAPI + PostgreSQL

### 🚀 **Prêt pour le Frontend**
- **Endpoints principaux** : 
  - `POST /zenith/import` - **NOUVEAU** Import depuis ZenithWakfu
  - `POST /search/build-from-text` - Création depuis texte
  - `GET /builds/{id}` - Récupération avec roadmap complète
- **Workflow simplifié** : 
  1. URL ZenithWakfu → `POST /zenith/import` → Build + Roadmap
  2. Texte libre → `POST /search/build-from-text` → Build + Roadmap
- **Une seule requête** : Plus besoin d'appels séparés
- **Administration** : Interface web pour gérer les zones (`/static/admin_zones.html`)
- **Documentation** : Voir `API_DOCUMENTATION.md` (v0.5.0)

### 🔧 **Améliorations Futures (Optionnelles)**
- [ ] Cache Redis pour performances
- [ ] Pagination pour résultats volumineux  
- [ ] Tests unitaires complets
- [ ] Docker et docker-compose
- [ ] Rate limiting et authentification
- [x] ~~Interface d'administration web~~ ✅ **Terminée** (zones)

## 🌐 Déploiement
- **Serveur** : LXC avec PostgreSQL
- **Proxy** : Nginx reverse proxy
- **SSL** : Let's Encrypt