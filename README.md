# WakDrop Backend

API backend pour analyser les builds Wakfu et générer des roadmaps de farm.

## Installation

```bash
pip install -r requirements.txt
cp .env.example .env
# Configurer la base de données dans .env
```

## Lancement

```bash
python main.py
```

API disponible sur http://localhost:8000  
Documentation sur http://localhost:8000/docs

## Endpoints principaux

- `POST /builds/` - Analyser un build Zenith
- `GET /builds/{id}/roadmap` - Roadmap de farm
- `POST /cdn/sync` - Synchroniser données Wakfu
- `GET /cdn/stats` - Statistiques du cache

## Base de données

Le projet utilise PostgreSQL avec SQLAlchemy. Les tables sont créées automatiquement au démarrage.