# 🎯 WakDrop API - Documentation Frontend

**Base URL**: `https://wakdropbackend-master-dev-mmangon.nabricot.pandabyte.ovh` (production)  
**API Version**: 0.6.1  
**Documentation interactive**: https://wakdropbackend-master-dev-mmangon.nabricot.pandabyte.ovh/docs

## 🆕 **Mise à jour v0.6.1** - Monstres dans Recherche d'Items

- 🎯 **NEW: Monstres dans `/search/items`** : L'endpoint retourne maintenant les monstres qui drop chaque item !
- 💧 **dropRate standardisé** : Format uniforme `dropRate` au lieu de `drop_rate`
- 🔧 **Fonction de recherche améliorée** : Gestion des apostrophes et accents
- 📊 **Base de données complète** : 8,959+ items avec drop rates corrigés
- ✅ **729 items ajoutés** depuis le bestiaire avec leurs drops

## 🆕 **Mise à jour v0.6.0** - Structure Plate & Performance

- 🎯 **BREAKING: Structure plate unifiée** : Tous les endpoints retournent maintenant une structure cohérente !
- ⚡ **Performance améliorée** : Import ZenithWakfu en ~7-10 secondes (50% plus rapide)
- 🔍 **Rareté extraite** : Les raretés sont maintenant détectées depuis ZenithWakfu
- 🚀 **Import depuis ZenithWakfu** : Workflow principal pour importer vos builds
- ✅ **Base de données enrichie** : 844 monstres avec 12,635+ drops

---

## ⚠️ **BREAKING CHANGES v0.6.0**

### Structure Plate Unifiée

**AVANT v0.6.0** (structure imbriquée) :
```javascript
// Accès compliqué aux données
const itemName = item.found_item.name
const itemRarity = item.found_item.rarity
const itemLevel = item.found_item.level
```

**MAINTENANT v0.6.0** (structure plate) :
```javascript
// Accès direct et simple
const itemName = item.name
const itemRarity = item.rarity  
const itemLevel = item.level
```

### Tous les endpoints concernés :
- ✅ `/zenith/import`
- ✅ `/builds/{id}` 
- ✅ `/search/build-from-text`
- ✅ `/search/items`

### Migration Frontend :
```javascript
// ANCIEN CODE (ne fonctionne plus)
items.forEach(item => {
  console.log(item.found_item.name)
})

// NOUVEAU CODE (v0.6.0+)
items.forEach(item => {
  console.log(item.name)
  console.log(item.rarity)     // Maintenant disponible partout !
  console.log(item.item_type)  // Type d'équipement
})
```

---

## 🔥 **Endpoints Principaux**

### 1. **Recherche d'Items** - `/search/items`

**L'endpoint le plus important** - Permet de rechercher des items par nom/texte avec **informations de drop**.

#### POST `/search/items`

```json
// Request
{
  "query": "épée",
  "limit": 10
}

// Response
[
  {
    "wakfu_id": 6121,
    "name": "Boufépée", 
    "level": 185,
    "item_type": "Arme",
    "rarity": "Rare",
    "match_score": 0.75,
    "obtention_type": "craft",
    "monsters": [
      {
        "id": 2083,
        "name": "Craqueboule Chuchoté",
        "level": null,
        "zone": "Zone Sombre",
        "dropRate": 0.8
      }
    ]
  }
]
```

**Utilisation dans Vue.js:**
```javascript
async searchItems(query) {
  const response = await fetch('https://wakdropbackend-master-dev-mmangon.nabricot.pandabyte.ovh/search/items', {
    method: 'POST', 
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, limit: 20 })
  })
  return response.json()
}

// Affichage des monstres qui droppent l'item
items.forEach(item => {
  console.log(`${item.name} (${item.rarity})`)
  item.monsters.forEach(monster => {
    console.log(`  - ${monster.name}: ${monster.dropRate}% (${monster.zone})`)
  })
})
```

---

### 2. **🚀 NEW: Import depuis ZenithWakfu** - `/zenith/import`

**Nouveau workflow principal** - Importez directement vos builds depuis ZenithWakfu !

**Fonctionnalités :**
- **Extraction automatique** des items depuis l'URL ZenithWakfu
- **Raretés authentiques** ZenithWakfu : `Légendaire`, `Épique`, `Relique`, `Rare`  
- **Mapping intelligent** avec la base de données locale
- **Génération immédiate** de la roadmap de farm

#### POST `/zenith/import`

```json
// Request
{
  "zenith_url": "https://www.zenithwakfu.com/builder/henpz",
  "build_name": "Mon Super Build" // optionnel
}

// Response - Structure PLATE v0.6.0
{
  "build_id": 123,
  "build_name": "Mon Super Build",
  "items_found": [
    {
      "wakfu_id": 29155,
      "name": "Heaume du Chevalier Creux",
      "level": 228,
      "item_type": "Coiffe",
      "rarity": "Légendaire", // ✅ Rareté authentique ZenithWakfu
      "match_score": 1.0,
      "obtention_type": "unknown"
    }
  ],
  "items_missing": [],
  "items_count": 13,
  "missing_count": 0,
  "farm_roadmap": {
    "monsters": {
      "5306": {
        "name": "Rushu",
        "items": [...]
      }
    },
    "zones_organized": [...],
    "summary": {
      "total_items": 13,
      "total_monsters": 18
    }
  },
  "created_at": "2025-09-07T09:41:10.716007+00:00"
}
```

**Utilisation dans Vue.js:**
```javascript
async importFromZenith(zenithUrl, buildName = null) {
  const response = await fetch('https://wakdropbackend-master-dev-mmangon.nabricot.pandabyte.ovh/zenith/import', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ 
      zenith_url: zenithUrl,
      build_name: buildName 
    })
  })
  
  if (!response.ok) {
    throw new Error(`Erreur ${response.status}: ${await response.text()}`)
  }
  
  return response.json()
}

// Utilisation
try {
  const result = await importFromZenith('https://www.zenithwakfu.com/builder/henpz', 'Mon Build')
  console.log(`Build créé avec ID: ${result.build_id}`)
  console.log(`Items trouvés: ${result.items_found.length}`)
  
  // Accéder à la roadmap complète
  const fullRoadmap = await fetch(`/builds/${result.build_id}`).then(r => r.json())
} catch (error) {
  console.error('Erreur import:', error.message)
}
```

**🔥 Avantages :**
- ⚡ **Ultra-rapide** : 7-10 secondes pour extraire un build complet (50% plus rapide)
- 🔍 **Rareté détectée** : Extrait automatiquement les raretés depuis ZenithWakfu
- 🎯 **Mapping automatique** : Trouve automatiquement les items dans votre base
- 📍 **Roadmap incluse** : Retourne directement la roadmap de farm
- 🏗️ **Structure unifiée** : Même format que tous les autres endpoints

---

### 3. **Créer Build depuis Texte** - `/search/build-from-text`

**Workflow principal** - L'utilisateur tape ses items en texte libre.

🆕 **Nouvelle fonctionnalité** : **Sélection automatique par rareté**  
Vous pouvez maintenant spécifier la rareté directement dans le texte !

#### POST `/search/build-from-text`

```json
// Request - Avec spécification de rareté
{
  "items_text": "Coiffe Primitive légendaire, Cape du Feu rare, Anneau PA mythique",
  "build_name": "Mon Build Tank"
}

// Request - Sans rareté (prend le premier résultat)
{
  "items_text": "Épée Iop, Cape du Feu, Anneau PA, Casque Sram",
  "build_name": "Mon Build Tank"
}

// Response - Structure PLATE v0.6.0
{
  "build_name": "Mon Build Tank",
  "items_found": [
    {
      "wakfu_id": 12345,
      "name": "Épée du Iop Suprême",
      "level": 200,
      "item_type": "Épée",
      "rarity": "Rare",
      "match_score": 0.85,
      "obtention_type": "craft"
    }
  ],
  "items_missing": ["Item inexistant"],
  "items_count": 3,
  "missing_count": 1,
  "farm_roadmap": {
    "priority_monsters": [
      {
        "monster_id": 123,
        "monster_name": "Dragon Cochon",
        "monster_level": 185,
        "zone": "Ile de Moon",
        "total_items": 2,
        "priority_score": 8.5,
        "dropped_items": [
          {
            "item_id": 12345,
            "item_name": "Épée du Iop",
            "drop_rate": 2.5
          }
          // ⚠️ Note: drop_rate est déjà en pourcentage (2.5 = 2.5%)
        ]
      }
    ],
    "stats": {
      "total_monsters": 5,
      "total_zones": 3,
      "estimated_time": "~4h de farm"
    }
  }
}
```

**Raretés supportées:**
- `commun` ou `inhabituel`
- `rare` 
- `mythique`
- `légendaire` (ou `legendaire`)
- `relique`
- `épique` (ou `epique`)

**Exemples d'utilisation:**
```
"Coiffe Primitive légendaire"     → Sélectionne la version Légendaire niveau 245
"Coiffe Primitive mythique"       → Sélectionne la version Mythique niveau 237  
"Épée Iop rare, Cape du Feu"     → Épée rare + Cape (premier résultat)
```

**Interface recommandée:**
```vue
<template>
  <div>
    <h2>🔍 Créer un Build</h2>
    <textarea 
      v-model="itemsText" 
      placeholder="Exemples: Coiffe Primitive légendaire, Cape du Feu rare, Anneau PA mythique"
      rows="3"
    ></textarea>
    <input v-model="buildName" placeholder="Nom du build (optionnel)" />
    <button @click="createBuild">Générer Roadmap</button>
    
    <!-- Résultats -->
    <div v-if="roadmap">
      <h3>✅ Build créé: {{ roadmap.items_count }} items</h3>
      <div v-if="roadmap.items_missing.length">
        <h4>⚠️ Items non trouvés:</h4>
        <ul>
          <li v-for="item in roadmap.items_missing" :key="item">{{ item }}</li>
        </ul>
      </div>
      
      <h3>🗺️ Roadmap de Farm</h3>
      <div v-for="monster in roadmap.farm_roadmap.priority_monsters" :key="monster.monster_id">
        <h4>{{ monster.monster_name }} (Niveau {{ monster.monster_level }})</h4>
        <p>📍 {{ monster.zone }} - Priorité: {{ monster.priority_score }}/10</p>
        <ul>
          <li v-for="item in monster.dropped_items" :key="item.item_id">
            {{ item.item_name }} ({{ item.dropRate }}% de drop)
          </li>
        </ul>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  data() {
    return {
      itemsText: '',
      buildName: '',
      roadmap: null
    }
  },
  methods: {
    async createBuild() {
      if (!this.itemsText.trim()) return
      
      const response = await fetch('https://wakdropbackend-master-dev-mmangon.nabricot.pandabyte.ovh/search/build-from-text', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          items_text: this.itemsText,
          build_name: this.buildName || 'Mon Build'
        })
      })
      
      if (response.ok) {
        this.roadmap = await response.json()
      } else {
        const error = await response.json()
        alert(`Erreur: ${error.detail}`)
      }
    }
  }
}
</script>
```

---

### 3. **Gestion des Builds** - `/builds/`

🆕 **Mise à jour majeure** : L'endpoint `/builds/{build_id}` retourne maintenant **la roadmap complète** !

#### GET `/builds/{build_id}` 🔥
**Nouveau** : Retourne les détails du build **avec sa roadmap complète**, identique à `/search/build-from-text`.

```json
// Response - Structure PLATE v0.6.0
{
  "build_id": 6,
  "build_name": "Mon Build Tank",
  "created_at": "2025-09-06T18:41:18.263523+00:00",
  "items_found": [
    {
      "wakfu_id": 29155,
      "name": "Heaume du Chevalier Creux",
      "level": 228,
      "item_type": "Coiffe",
      "rarity": "Légendaire", // ✅ Rareté authentique ZenithWakfu
      "match_score": 1.0,
      "obtention_type": "unknown"
    }
  ],
  "items_missing": [],
  "items_count": 2,
  "missing_count": 0,
  "farm_roadmap": {
    "zones_organized": [
      {
        "name": "Spirale du vide",
        "total_items": 2,
        "avg_drop_rate": 0.625,
        "expanded": false,
        "monsters": [
          {
            "id": 5283,
            "name": "Ar'Nan, Augure du néant",
            "level": null,
            "items": [
              {
                "item_id": 29155,
                "drop_rate": 1.0
              },
              {
                "item_id": 29156,
                "drop_rate": 0.25
              }
            ]
          }
        ]
      }
    ],
    "zones": {...},
    "monsters": {...},
    "summary": {
      "total_items": 2,
      "total_zones": 1,
      "total_monsters": 1
    }
  }
}
```

**Avantages de cette mise à jour :**
- ✅ **Une seule requête** au lieu de deux (`/builds/{id}` + `/builds/{id}/roadmap`)
- ✅ **Structure identique** à `/search/build-from-text` pour une intégration facilitée
- ✅ **Détails complets** : nom des items, niveaux, raretés, zones organisées
- ✅ **Gestion des erreurs** : items manquants du cache affichés clairement

**Utilisation dans Vue.js :**
```javascript
// Avant : 2 requêtes
const build = await fetch(`/builds/${buildId}`).then(r => r.json())
const roadmap = await fetch(`/builds/${buildId}/roadmap`).then(r => r.json())

// Maintenant : 1 seule requête !
const buildWithRoadmap = await fetch(`/builds/${buildId}`).then(r => r.json())
// → Contient directement build_id, build_name, items_found, farm_roadmap, etc.
```

#### POST `/builds/`
```json
// Request
{
  "build_name": "Build PvP",
  "items_ids": [12345, 67890, 11111]
}
```

#### GET `/builds/{build_id}/roadmap`
⚠️ **Déprécié mais maintenu** : Utilisez directement `/builds/{build_id}` qui contient la roadmap.
Génère uniquement la roadmap de farm pour un build existant.

---

### 4. **Données de Drop** - `/drops/` 🆕

Les endpoints de drops incluent maintenant les **zones associées** !

#### GET `/drops/item/{item_id}`
Récupère tous les monstres qui drop un item avec leurs zones.

```json
// GET /drops/item/26581 (Coiffetière)
[
  {
    "monster_id": 4998,
    "monster_name": "Abrasif le décapant",
    "monster_level": null,
    "item_id": 26581,
    "drop_rate": 0.72,
    "zone_name": "Bonta"    // 🆕 Zone associée !
  },
  {
    "monster_id": 4874,
    "monster_name": "Chêne Mou", 
    "drop_rate": 0.72,
    "zone_name": "Bonta"
  }
]
```

#### GET `/drops/monster/{monster_id}`
Récupère tous les items qu'un monstre peut drop.

#### POST `/drops/farm-roadmap`
Génère une roadmap de farm optimisée pour plusieurs items.

```json
// Request
{
  "item_ids": [12582, 23647]  // DéCape rare et mythique
}

// Response  
{
  "priority_monsters": [
    {
      "monster_name": "Bouftou Sauvage",
      "zone": "Plaine des Bouftous",  // 🆕 Zone incluse
      "total_items": 2,
      "dropped_items": [
        {"item_name": "DéCape", "dropRate": 0.8}
      ]
    }
  ]
}
```

#### GET `/drops/stats`
Statistiques des données en base :
- **12,635 drops** au total
- **844 monstres** uniques  
- **5,646 items** avec des drops

#### POST `/drops/import`
Import de données depuis fichiers JSON externes.

#### DELETE `/drops/clear`
⚠️ Supprime toutes les données de drop.

---

### 5. **Administration des Zones** - `/admin/zones/` 🆕

Interface complète pour gérer les zones et associer les monstres.

#### GET `/admin/zones/zones`
Liste toutes les zones avec le nombre de monstres.

```json
[
  {
    "id": 1,
    "name": "Bonta",
    "description": "Cité de Bonta",
    "min_level": 1,
    "max_level": 200,
    "monster_count": 15
  }
]
```

#### POST `/admin/zones/zones`
Crée une nouvelle zone.

```json
// Request
{
  "name": "Île de Moon",
  "description": "Zone de haut niveau",
  "min_level": 180,
  "max_level": 200
}
```

#### GET `/admin/zones/zones/{zone_id}`
Détails d'une zone avec tous ses monstres.

```json
{
  "id": 1,
  "name": "Bonta", 
  "monsters": [
    {
      "monster_id": 4998,
      "monster_name": "Abrasif le décapant"
    }
  ]
}
```

#### POST `/admin/zones/zones/{zone_id}/monsters`
Ajoute un monstre à une zone.

```json
// Request
{
  "monster_id": 4998
}
```

#### DELETE `/admin/zones/zones/{zone_id}/monsters/{monster_id}`
Retire un monstre d'une zone.

#### GET `/admin/zones/monsters/search`
Recherche des monstres pour l'interface admin.

```bash
GET /admin/zones/monsters/search?q=abra&limit=5
# → Retourne les monstres contenant "abra"
```

**🌐 Interface Web** : `/static/admin_zones.html`
Interface graphique complète pour gérer les zones.

---

### 6. **Informations Items** - `/items/`

#### GET `/items/{item_id}`
```json
{
  "wakfu_id": 12345,
  "name": "Épée du Iop Suprême",
  "level": 200,
  "data_json": {
    "title": { "fr": "Épée du Iop Suprême" },
    "level": 200,
    "definition": { "item": { "rarity": 3 } }
  },
  "obtention_type": "drop",
  "last_updated": "2024-01-15T08:00:00"
}
```

---

### 5. **Données de Drop** - `/drops/`

#### GET `/drops/item/{item_id}`
Tous les monstres qui drop cet item.

#### GET `/drops/monster/{monster_id}` 
Tous les items d'un monstre.

---

## 🎨 **Interface Utilisateur Recommandée**

### **Page Principale - Créer Build**
```vue
<template>
  <div class="create-build">
    <h1>🎯 WakDrop - Créer votre Build</h1>
    
    <!-- Méthode principale: Texte libre -->
    <div class="text-input-method">
      <h2>✨ Méthode Simple</h2>
      <p>Tapez vos items en texte libre, séparés par des virgules:</p>
      <textarea 
        v-model="itemsText"
        placeholder="Exemples: Coiffe Primitive légendaire, Cape du feu rare, Anneau PA mythique"
        class="items-textarea"
      ></textarea>
      <input 
        v-model="buildName" 
        placeholder="Nom du build (optionnel)"
        class="build-name-input"
      />
      <button @click="createBuildFromText" class="primary-btn">
        🚀 Générer Roadmap
      </button>
    </div>

    <!-- Méthode avancée: Recherche item par item -->
    <details class="advanced-method">
      <summary>🔧 Méthode Avancée</summary>
      <div class="search-items">
        <input 
          v-model="searchQuery"
          @input="searchItems"
          placeholder="Rechercher un item: épée, cape, anneau..."
        />
        <div v-if="searchResults.length" class="search-results">
          <div 
            v-for="item in searchResults" 
            :key="item.wakfu_id"
            @click="addItem(item)"
            class="item-result"
          >
            <strong>{{ item.name }}</strong>
            <span>Niveau {{ item.level }} - {{ item.rarity }}</span>
            <span>Score: {{ item.match_score.toFixed(2) }}</span>
          </div>
        </div>
        
        <div v-if="selectedItems.length" class="selected-items">
          <h3>Items sélectionnés:</h3>
          <div 
            v-for="item in selectedItems" 
            :key="item.wakfu_id"
            class="selected-item"
          >
            {{ item.name }}
            <button @click="removeItem(item)">❌</button>
          </div>
        </div>
      </div>
    </details>

    <!-- Résultats -->
    <div v-if="buildResult" class="build-results">
      <!-- Affichage des résultats comme dans l'exemple précédent -->
    </div>
  </div>
</template>
```

---

## 🔧 **Configuration Axios (optionnel)**

```javascript
// plugins/api.js
import axios from 'axios'

const api = axios.create({
  baseURL: 'https://wakdropbackend-master-dev-mmangon.nabricot.pandabyte.ovh',
  headers: {
    'Content-Type': 'application/json'
  }
})

export default {
  // Recherche items
  searchItems: (query, limit = 20) => 
    api.post('/search/items', { query, limit }),
  
  // Créer build depuis texte
  createBuildFromText: (items_text, build_name) =>
    api.post('/search/build-from-text', { items_text, build_name }),
  
  // Gestion builds
  getBuild: (build_id) => api.get(`/builds/${build_id}`),
  getBuildRoadmap: (build_id) => api.get(`/builds/${build_id}/roadmap`),
  
  // Items
  getItem: (item_id) => api.get(`/items/${item_id}`),
  
  // Drops
  getItemDrops: (item_id) => api.get(`/drops/item/${item_id}`),
  getMonsterDrops: (monster_id) => api.get(`/drops/monster/${monster_id}`)
}
```

---

## ⚡ **Workflow Utilisateur Final**

1. **Utilisateur** tape: `"Coiffe Primitive légendaire, Cape du feu rare, Anneau PA"`
2. **Frontend** appelle: `POST /search/build-from-text`
3. **API** trouve automatiquement les items correspondants **avec la bonne rareté**
4. **API** génère la roadmap avec les monstres à farmer **pour ces items précis**
5. **Frontend** affiche la roadmap avec zones et taux de drop

🆕 **Nouveau** : L'API sélectionne automatiquement la **bonne variante** d'item selon la rareté spécifiée !

**C'est tout !** Plus besoin de Zenith, tout est automatique. 🎉

---

## 🚨 **Gestion d'Erreurs**

```javascript
try {
  const response = await api.createBuildFromText(itemsText, buildName)
  // Succès
} catch (error) {
  if (error.response?.status === 400) {
    // Erreur de validation
    alert(error.response.data.detail)
  } else if (error.response?.status === 404) {
    // Aucun item trouvé
    alert("Aucun item trouvé avec ce texte")
  } else {
    // Erreur serveur
    alert("Erreur serveur, réessayez plus tard")
  }
}
```

---

## 🗺️ **Administration des Zones**

### Interface Web d'Administration

**URL**: https://wakdropbackend-master-dev-mmangon.nabricot.pandabyte.ovh/static/admin_zones.html

Interface graphique simple pour gérer les zones et associer les monstres aux zones.

**Fonctionnalités:**
- ✅ Créer/supprimer des zones
- ✅ Recherche intelligente de monstres
- ✅ Association monstre/zone avec fréquence d'apparition
- ✅ Interface responsive et intuitive

### Endpoints API Zones

#### GET `/admin/zones/zones`
Liste toutes les zones avec le nombre de monstres.

```json
// Response
[
  {
    "id": 1,
    "name": "Île de Moon",
    "description": "Zone de niveau élevé avec des boss puissants",
    "min_level": 180,
    "max_level": 200,
    "monster_count": 5
  }
]
```

#### POST `/admin/zones/zones`
Crée une nouvelle zone.

```json
// Request
{
  "name": "Nouvelle Zone",
  "description": "Description optionnelle",
  "min_level": 100,
  "max_level": 120
}

// Response
{
  "id": 2,
  "name": "Nouvelle Zone",
  "description": "Description optionnelle", 
  "min_level": 100,
  "max_level": 120,
  "monster_count": 0
}
```

#### GET `/admin/zones/zones/{zone_id}`
Détails d'une zone avec tous ses monstres.

```json
// Response
{
  "id": 1,
  "name": "Île de Moon",
  "description": "Zone de niveau élevé",
  "min_level": 180,
  "max_level": 200,
  "monster_count": 2,
  "monsters": [
    {
      "monster_id": 4909,
      "monster_name": "Scaraboss",
      "spawn_frequency": "Boss",
      "notes": "Archimonstre principal de la zone"
    }
  ]
}
```

#### DELETE `/admin/zones/zones/{zone_id}`
Supprime une zone et toutes ses associations.

#### POST `/admin/zones/zones/{zone_id}/monsters`
Ajoute un monstre à une zone.

```json
// Request
{
  "monster_id": 4909,
  "spawn_frequency": "Boss",
  "notes": "Archimonstre principal"
}
```

#### DELETE `/admin/zones/zones/{zone_id}/monsters/{monster_id}`
Retire un monstre d'une zone.

#### GET `/admin/zones/monsters/search`
Recherche des monstres pour l'interface admin.

**Paramètres:**
- `q` (string): Terme de recherche
- `limit` (int): Nombre maximum de résultats (défaut: 20)

```json
// Response
[
  {
    "monster_id": 4909,
    "monster_name": "Scaraboss"
  }
]
```

### Utilisation dans le Frontend

```javascript
// Charger les zones
async function loadZones() {
  const response = await fetch('/admin/zones/zones');
  const zones = await response.json();
  return zones;
}

// Créer une zone
async function createZone(zoneData) {
  const response = await fetch('/admin/zones/zones', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(zoneData)
  });
  return response.json();
}

// Rechercher des monstres
async function searchMonsters(query) {
  const response = await fetch(`/admin/zones/monsters/search?q=${encodeURIComponent(query)}`);
  return response.json();
}
```