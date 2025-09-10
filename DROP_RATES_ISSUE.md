# ⚠️ PROBLÈME IDENTIFIÉ - Taux de Drop Incorrects

## 📊 Problème Constaté

Les taux de drop dans la base de données semblent être **10x trop élevés** pour les items légendaires.

### Exemples Actuels (INCORRECTS)
- **Plastron d'Enter** (Légendaire) : `0.4%` sur Chrysavide, Inanite, Echinoidéant
- **Heaume du Chevalier Creux** (Légendaire) : `1.0%` sur Ar'Nan
- **Bottes de mauvais Augure** (Légendaire) : `0.5%` sur Ar'Nan

### Taux Réalistes (selon Wiki Wakfu)
- Items **Légendaires** : `0.01% - 0.05%` (très rares)
- Items **Épiques** : `0.05% - 0.2%` (rares)
- Items **Rares** : `0.2% - 1%` (peu communs)
- Items **Communs** : `1% - 5%` (fréquents)

## 🔍 Origine du Problème

Les données ont été importées depuis des scripts de scraping externes. Il est possible que :
1. La source avait déjà des taux incorrects
2. Une erreur de conversion s'est produite lors de l'import
3. Les taux étaient en "pour mille" (‰) et non en pourcentage (%)

## 🔧 Solution Proposée

### Option 1 : Diviser par 10 les taux suspects
```sql
-- Corriger les taux trop élevés pour les items de haut niveau
UPDATE monster_drops 
SET drop_rate = drop_rate / 10
WHERE item_id IN (
    SELECT wakfu_id 
    FROM cached_items 
    WHERE data_json->>'definition'->>'item'->>'level' > 200
)
AND drop_rate > 0.1;
```

### Option 2 : Réimporter depuis une source fiable
- Utiliser les données du Wiki Wakfu officiel
- Vérifier avec la communauté Wakfu

## 📝 Notes

- **Date de découverte** : 2025-09-07
- **Impact** : Les roadmaps de farm sont trop optimistes
- **Priorité** : HAUTE - Les joueurs pourraient être déçus par les vrais taux

## ⚠️ ACTION REQUISE

Les taux de drop doivent être vérifiés et corrigés avant mise en production !

### Items à Vérifier en Priorité
1. Tous les items niveau 200+
2. Tous les items avec rareté "Légendaire" ou "Épique"
3. Tous les taux > 0.5% pour des items rares

---
**À faire** : 
- [ ] Vérifier la source originale des données
- [ ] Comparer avec le Wiki Wakfu
- [ ] Corriger les taux incorrects
- [ ] Mettre à jour la documentation