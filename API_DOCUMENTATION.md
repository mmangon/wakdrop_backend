# 🎯 WakDrop API - Documentation Frontend

**Base URL**: `http://localhost:8000` (développement)  
**API Version**: 0.2.0  
**Documentation interactive**: http://localhost:8000/docs

---

## 🔥 **Endpoints Principaux**

### 1. **Recherche d'Items** - `/search/items`

**L'endpoint le plus important** - Permet de rechercher des items par nom/texte.

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
    "obtention_type": "craft"
  }
]
```

**Utilisation dans Vue.js:**
```javascript
async searchItems(query) {
  const response = await fetch('http://localhost:8000/search/items', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query, limit: 20 })
  })
  return response.json()
}
```

---

### 2. **Créer Build depuis Texte** - `/search/build-from-text`

**Workflow principal** - L'utilisateur tape ses items en texte libre.

#### POST `/search/build-from-text`

```json
// Request
{
  "items_text": "Épée Iop, Cape du Feu, Anneau PA, Casque Sram",
  "build_name": "Mon Build Tank"
}

// Response
{
  "build_name": "Mon Build Tank",
  "items_found": [
    {
      "input_name": "Épée Iop",
      "found_item": {
        "wakfu_id": 12345,
        "name": "Épée du Iop Suprême",
        "level": 200,
        "match_score": 0.85
      },
      "wakfu_id": 12345
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

**Interface recommandée:**
```vue
<template>
  <div>
    <h2>🔍 Créer un Build</h2>
    <textarea 
      v-model="itemsText" 
      placeholder="Tapez vos items: Épée Iop, Cape du Feu, Anneau PA..."
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
            {{ item.item_name }} ({{ item.drop_rate }}% de drop)
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
      
      const response = await fetch('http://localhost:8000/search/build-from-text', {
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

#### GET `/builds/{build_id}`
```json
{
  "id": 1,
  "zenith_url": null,
  "zenith_id": "Mon Build Tank", 
  "items_ids": [12345, 67890],
  "created_at": "2024-01-15T10:30:00"
}
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
Génère la roadmap de farm pour un build existant.

---

### 4. **Informations Items** - `/items/`

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
        placeholder="Exemple: Épée Iop niveau 200, Cape du feu, Anneau PA, Bottes terre"
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
  baseURL: 'http://localhost:8000',
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

1. **Utilisateur** tape: `"Épée Iop, Cape du feu, Anneau PA"`
2. **Frontend** appelle: `POST /search/build-from-text`
3. **API** trouve automatiquement les items correspondants
4. **API** génère la roadmap avec les monstres à farmer
5. **Frontend** affiche la roadmap avec zones et taux de drop

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