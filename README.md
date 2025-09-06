# 🎮 WakDrop Backend

API REST pour créer des builds Wakfu et générer des **roadmaps de farm détaillées**. Indique **quels monstres farmer**, dans **quelles zones**, avec les **taux de drop** précis.

## ✨ Fonctionnalités

- 🔍 **Recherche intelligente d'items** - Par texte libre avec scoring de pertinence
- 🎯 **Création de builds depuis texte** - "Épée Iop, Cape du Feu, Anneau PA"
- 🗺️ **Roadmaps optimisées** - Génération automatique par zones avec priorités
- 🔄 **Sync CDN Wakfu** - 8,230+ items synchronisés automatiquement
- 👾 **Base de données complète** - 844 monstres avec 12,635+ drops pré-importés
- 🏛️ **Administration des zones** - Interface web pour gérer les zones et monstres
- 📦 **API unifiée** - Structure identique entre création et récupération de builds

## 🛠️ Stack Technique

- **FastAPI** 0.104.1 - Framework web moderne et performant
- **PostgreSQL** - Base de données avec support JSON
- **SQLAlchemy** 2.0 - ORM Python
- **httpx** - Client HTTP asynchrone pour CDN Wakfu
- **Recherche intelligente** - Algorithme de matching avec scores de pertinence

## 📋 Prérequis

- Python 3.9+
- PostgreSQL

## 🚀 Installation

### 1. Cloner et installer

```bash
# Cloner le projet
git clone [votre-repo]
cd wakdropbackend

# Environnement virtuel
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows

# Installer les dépendances
pip install -r requirements.txt
pip install pydantic-settings beautifulsoup4 selenium
```

### 2. Configuration

```bash
# Copier le fichier d'exemple
cp .env.example .env

# Éditer .env avec vos paramètres
DATABASE_URL=postgresql://user:password@localhost:5432/wakdrop
WAKFU_CDN_BASE_URL=https://wakfu.cdn.ankama.com/gamedata
WAKFU_VERSION=1.88.1.39
```

### 3. Initialisation (première fois)

```bash
# Méthode 1: Script automatique (recommandé)
python initialize.py

# Méthode 2: Via l'API (après lancement du serveur)
curl -X POST http://localhost:8000/admin/initialize
```

### 4. Lancement

```bash
# Développement
python main.py

# Production
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

📖 **Documentation interactive**: http://localhost:8000/docs

## 🎯 Utilisation Rapide

### Créer un build depuis du texte

```bash
# 1. Créer un build depuis du texte libre
curl -X POST http://localhost:8000/search/build-from-text \
  -H "Content-Type: application/json" \
  -d '{"items_text": "Épée Iop, Cape du Feu, Anneau PA", "build_name": "Mon Build Tank"}'

# 2. Récupérer un build avec sa roadmap complète
curl http://localhost:8000/builds/1
```

### Résultat exemple

```json
{
  "build_name": "Mon Build Tank",
  "items_found": [
    {
      "input_name": "Épée Iop",
      "found_item": {
        "wakfu_id": 12345,
        "name": "Épée du Iop Suprême",
        "level": 200,
        "rarity": "Légendaire",
        "match_score": 0.85
      }
    }
  ],
  "items_missing": [],
  "items_count": 3,
  "farm_roadmap": {
    "zones_organized": [
      {
        "name": "Spirale du vide",
        "total_items": 2,
        "avg_drop_rate": 0.625,
        "monsters": [
          {
            "id": 5283,
            "name": "Ar'Nan, Augure du néant",
            "items": [
              {"item_id": 12345, "drop_rate": 1.0}
            ]
          }
        ]
      }
    ],
    "summary": {
      "total_items": 3,
      "total_zones": 1,
      "total_monsters": 1
    }
  }
}
```

## 📚 Endpoints Principaux

### Recherche et Builds
- `POST /search/items` - Recherche d'items par texte libre
- `POST /search/build-from-text` - **Endpoint principal** - Créer build depuis texte
- `GET /builds/{id}` - **Nouveau** - Récupère build avec roadmap complète
- `POST /builds/` - Créer build depuis liste d'items

### Données de Drop
- `GET /drops/item/{item_id}` - Monstres qui drop un item
- `POST /drops/farm-roadmap` - Roadmap optimisée pour liste d'items
- `GET /drops/stats` - Statistiques des données

### Administration
- `POST /admin/initialize` - Initialisation complète du système
- `GET /admin/zones/zones` - Interface de gestion des zones
- `GET /admin/system-info` - État du système

### CDN et Cache
- `POST /cdn/sync` - Synchronisation avec le CDN Wakfu
- `GET /items/{id}` - Détails d'un item depuis le cache

Voir tous les endpoints: http://localhost:8000/docs

## 🔄 Workflow

### Création de Build
1. **Frontend Vue.js** envoie du texte libre: "Épée Iop, Cape du Feu, Anneau PA"
2. **Backend recherche** les items correspondants avec scoring intelligent
3. **Analyse automatique** des monstres qui drop ces items
4. **Génération** d'une roadmap optimisée par zones avec priorités
5. **Affichage** dans le frontend avec zones organisées et taux de drop

### Récupération de Build
1. **Frontend** demande: `GET /builds/{id}`
2. **Backend retourne** directement build + roadmap complète
3. **Structure identique** à la création pour faciliter l'intégration

## 🐛 Troubleshooting

### Erreur PostgreSQL
```bash
# Vérifier que PostgreSQL est lancé
sudo service postgresql status

# Créer la base si nécessaire
createdb wakdrop
```

### Pas de données d'items
```bash
# Synchroniser avec le CDN Wakfu
curl -X POST http://localhost:8000/cdn/sync

# Vérifier les statistiques
curl http://localhost:8000/cdn/stats
```

### Pas de données de drop
```bash
# Vérifier les statistiques des drops
curl http://localhost:8000/drops/stats

# Les données sont pré-importées à l'initialisation
curl -X POST http://localhost:8000/admin/initialize
```

## 📝 License

MIT

## 🤝 Contribution

Les contributions sont bienvenues ! N'hésitez pas à ouvrir une issue ou une PR.

## 📧 Contact

Pour toute question sur le backend, consultez la documentation complète dans `CLAUDE.md`