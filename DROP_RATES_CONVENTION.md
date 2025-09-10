# Convention des Drop Rates - WakDrop Backend

## ⚠️ IMPORTANT - À LIRE ABSOLUMENT

### 📊 Format des Drop Rates

Les taux de drop dans la base de données sont **DÉJÀ exprimés en pourcentage**.

#### Exemples de valeurs dans la base :
- `0.04` = **0.04%** (ultra rare, 4 chances sur 10 000)
- `0.1` = **0.1%** (très rare, 1 chance sur 1000)
- `0.4` = **0.4%** (rare, 4 chances sur 1000)
- `0.5` = **0.5%** (rare, 1 chance sur 200)
- `1.0` = **1.0%** (peu commun, 1 chance sur 100)
- `2.0` = **2.0%** (commun, 1 chance sur 50)

### ❌ Erreur Fréquente

**NE PAS** interpréter `0.4` comme 40% !
**NE PAS** multiplier par 100 pour l'affichage !

### ✅ Utilisation Correcte

#### Dans le code backend :
```python
drop_rate = 0.4  # Stocké en base comme 0.4
drop_percentage = f"{drop_rate}%"  # Affichage : "0.4%"
```

#### Dans l'API Response :
```json
{
  "drop_rate": 0.4,           // Valeur numérique
  "drop_percentage": "0.4%"    // String formaté pour affichage
}
```

#### Dans le frontend :
```javascript
// CORRECT
const displayRate = `${dropRate}%`;  // "0.4%"

// INCORRECT ❌
const displayRate = `${dropRate * 100}%`;  // "40%" - FAUX !
```

### 📝 Raison de cette Convention

Cette convention vient du fait que les données de drop ont été importées depuis des sources externes (scripts de scraping) qui utilisaient déjà ce format. 

Les taux de drop dans Wakfu sont généralement très faibles (souvent < 1%), donc stocker `0.4` pour 0.4% est plus naturel que stocker `0.004`.

### 🔄 Modifications du Code

Le 2025-09-07, le `drop_manager.py` a été modifié pour ajouter automatiquement le champ `drop_percentage` formaté dans les réponses API (ligne 196).

### 📋 Fichiers Concernés
- `/services/drop_manager.py` : Génère les roadmaps avec drop rates
- `/models/cache.py` : Modèle MonsterDrop avec field `drop_rate`
- `/routers/drops.py` : Endpoints retournant les drop rates
- `/routers/zenith.py` : Import des builds avec roadmap
- `/routers/builds.py` : Récupération des builds avec roadmap

### 🎯 Points de Vérification
1. Lors de l'import de nouvelles données de drop
2. Lors de l'affichage dans le frontend
3. Lors de la création de nouvelles fonctionnalités utilisant les drop rates

---
**Date de création** : 2025-09-07
**Dernière mise à jour** : 2025-09-07