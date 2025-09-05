# WakDrop Backend - API FastAPI

## 🎯 Objectif
API backend pour analyser les builds Wakfu et générer des roadmaps de farm optimisées.

## ⚙️ Stack Technique
- **Framework** : FastAPI 0.104.1
- **Database** : PostgreSQL + SQLAlchemy
- **HTTP Client** : httpx (pour CDN et Zenith)
- **Python** : 3.9+

## 🏗️ Architecture
```
wakdrop_backend/
├── models/          # SQLAlchemy models
│   ├── build.py     # Builds Zenith
│   └── cache.py     # Cache items CDN + analyses
├── services/        
│   ├── wakfu_cdn.py # Sync CDN Wakfu + analyse obtention
│   ├── zenith.py    # Parse builds Zenith
│   └── analysis.py  # Génération roadmaps farm
├── routers/         # Endpoints FastAPI
│   ├── builds.py    # CRUD builds
│   ├── items.py     # Détails items 
│   └── cdn.py       # Sync CDN
├── core/            # Config, DB, dependencies
└── main.py          # App FastAPI
```

## 📡 Sources de Données

### CDN Wakfu Officiel
- **URL** : `https://wakfu.cdn.ankama.com/gamedata/{version}/`
- **Version actuelle** : 1.88.1.39 (via config.json)
- **Types utilisés** :
  - `items.json` - Équipements, stats, effets (~20Mo)
  - `recipes.json` + `recipeIngredients.json` - Système craft
  - `harvestLoots.json` + `collectibleResources.json` - Ressources
  - `itemProperties.json` - Propriétés spéciales

### Zenith Wakfu
- **Format URL** : `https://www.zenithwakfu.com/builder/{build_id}`
- **Parse** : Extraction JavaScript des équipements

## 🚀 Endpoints API

### Builds
- `POST /builds/` - Parse build Zenith + sauvegarde
- `GET /builds/{id}` - Détails build
- `GET /builds/{id}/roadmap` - Roadmap de farm complète

### Items  
- `GET /items/{id}` - Détails item depuis cache
- `GET /items/{id}/obtention` - Infos obtention détaillées

### CDN
- `POST /cdn/sync` - Sync données CDN (background task)
- `GET /cdn/version` - Version CDN actuelle
- `GET /cdn/stats` - Stats cache (nb items par type)

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

## 🔄 Workflow Backend

1. **Parse Zenith** → Extrait items_ids depuis URL
2. **Sync CDN** → Cache items + analyse obtention
3. **Generate Roadmap** → Croise build + cache → roadmap

## ⚙️ Configuration

### Variables d'environnement (.env)
```bash
DATABASE_URL=postgresql://user:pass@localhost:5432/wakdrop
WAKFU_CDN_BASE_URL=https://wakfu.cdn.ankama.com/gamedata
WAKFU_VERSION=1.88.1.39
```

## 🚀 Lancement

### Installation
```bash
pip install -r requirements.txt
cp .env.example .env  # Puis éditer
```

### Développement  
```bash
python main.py
# API: http://localhost:8000
# Docs: http://localhost:8000/docs
```

### Production
```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

## 📋 Commandes Utiles
- `uvicorn main:app --reload` - Serveur dev avec auto-reload
- `python -c "from core.database import engine, Base; Base.metadata.create_all(engine)"` - Créer tables

## 🔧 TODO Backend
- [ ] Affiner parsing Zenith (structure JavaScript réelle)
- [ ] Optimiser sync CDN (pagination, diff)
- [ ] Ajouter cache Redis pour performances
- [ ] Background jobs (Celery/APScheduler)
- [ ] Tests unitaires
- [ ] Monitoring/logs
- [ ] Rate limiting

## 🌐 Déploiement
- **Serveur** : LXC avec PostgreSQL
- **Proxy** : Nginx reverse proxy
- **SSL** : Let's Encrypt