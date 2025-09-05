# 🎮 WakDrop Backend

API REST pour analyser les builds Wakfu et générer des roadmaps de farm optimisées. Indique **quels monstres farmer**, dans **quelles zones**, avec les **taux de drop** précis.

## ✨ Fonctionnalités

- 🏗️ **Parse des builds Zenith** - Extraction automatique des équipements
- 👾 **Scraping des drops** - Récupération des données depuis l'encyclopédie Wakfu  
- 📊 **Roadmaps optimisées** - Génération de parcours de farm par zones
- 🔄 **Sync CDN Wakfu** - Mise à jour des items, recettes, récoltes
- 📦 **Cache intelligent** - Stockage PostgreSQL pour performances optimales

## 🛠️ Stack Technique

- **FastAPI** 0.104.1 - Framework web moderne et performant
- **PostgreSQL** - Base de données avec support JSON
- **SQLAlchemy** 2.0 - ORM Python
- **Selenium** - Scraping de l'encyclopédie Wakfu
- **httpx** - Client HTTP asynchrone

## 📋 Prérequis

- Python 3.9+
- PostgreSQL
- Chrome/Chromium (pour Selenium)

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
python initialize.py --pages 5 --headless

# Méthode 2: Via l'API
python main.py
# Dans un autre terminal:
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

### Analyser un build Zenith

```bash
# 1. Parser le build
curl -X POST http://localhost:8000/builds/ \
  -H "Content-Type: application/json" \
  -d '{"zenith_url": "https://www.zenithwakfu.com/builder/xxxxx"}'

# 2. Récupérer la roadmap de farm
curl http://localhost:8000/builds/1/roadmap
```

### Résultat exemple

```json
{
  "zones": {
    "Astrub": {
      "monsters": [12, 34, 56],
      "total_items": 5,
      "avg_drop_rate": 15.5
    }
  },
  "monsters": {
    "12": {
      "name": "Bouftou",
      "level": 10,
      "items": [
        {"item_id": 789, "drop_rate": 25.0}
      ]
    }
  }
}
```

## 📚 Endpoints Principaux

### Builds
- `POST /builds/` - Parse un build Zenith
- `GET /builds/{id}/roadmap` - Génère la roadmap de farm

### Drops
- `POST /drops/farm-roadmap` - Roadmap pour liste d'items
- `POST /drops/scrape` - Lance le scraping de monstres
- `GET /drops/stats` - Statistiques des données

### Admin
- `POST /admin/initialize` - Initialisation complète
- `GET /admin/system-info` - État du système

Voir tous les endpoints: http://localhost:8000/docs

## 🔄 Workflow

1. **Frontend Vue.js** envoie l'URL Zenith
2. **Backend parse** les équipements du build
3. **Analyse** des monstres qui drop ces items
4. **Génération** d'une roadmap optimisée par zones
5. **Affichage** dans le frontend avec taux de drop

## 🐛 Troubleshooting

### Erreur PostgreSQL
```bash
# Vérifier que PostgreSQL est lancé
sudo service postgresql status

# Créer la base si nécessaire
createdb wakdrop
```

### Erreur Selenium
```bash
# Installer Chrome/Chromium
sudo apt install chromium-browser

# Ou utiliser mode headless
python initialize.py --headless
```

### Pas de données de drop
```bash
# Lancer le scraping initial (5 pages = ~100 monstres)
curl -X POST http://localhost:8000/drops/scrape \
  -d '{"start_page": 1, "end_page": 5}'
```

## 📝 License

MIT

## 🤝 Contribution

Les contributions sont bienvenues ! N'hésitez pas à ouvrir une issue ou une PR.

## 📧 Contact

Pour toute question sur le backend, consultez la documentation complète dans `CLAUDE.md`