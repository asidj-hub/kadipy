# Suivi des tâches — KadiPy

**Dernière mise à jour :** 6 août 2026
**Sources :** audit du code source + croisement de trois documents de référence
(`analyse_00.md`, `analyse_1.0.0.md`, `suivi.md` v1.1.0)

**Légende :**
- `[x]` Terminé
- `[-]` En cours
- `[ ]` À faire
- `[~]` Reporté (version ultérieure précisée)

---

## État général du projet

| Version | Statut | Périmètre |
|---------|--------|-----------|
| v1.0.0 | Livrée | Version initiale avec 17 problèmes identifiés |
| v1.1.0 | Livrée | 17 corrections + intégration API WFP DataBridges |
| +v1.1.0 | Planifiée | Corrections de sécurité + benchmarks |
| v1.2.0 | Planifiée | Penman-Monteith, MAEP, notebook interactif |
| v2.0.0 | Planifiée | Prophet, interface web, transport multimodal |

---

## Partie A — Tâches v1.1.0 (terminées)

Toutes les tâches ci-dessous ont été vérifiées directement dans le code source.

### Corrections bloquantes

| # | Module | Sévérité | Description | Statut |
|---|--------|----------|-------------|--------|
| P8 | `kidas` | Critique | Rapport `execute()` aligné sur la documentation publique | `[x]` |
| P6 | `market` | Haute | `storage_vs_sell_now()` propage le vrai flag `is_simulated` | `[x]` |
| P13 | Infrastructure | Haute | `requirements.txt` réécrit comme alias vers `pyproject.toml` | `[x]` |
| P3 | `weather` | Haute | SPI calculé via loi Gamma (McKee et al. 1993) | `[x]` |
| P4 | `market` | Haute | Bornes GPS lues depuis `CONFIG` (non codées en dur) | `[x]` |
| P9 | `kidas` | Haute | `fix_dates()` accumule correctement le compteur de corrections | `[x]` |
| P5 | `market` | Moyenne | `get_market_functionality_index()` lève `NotImplementedError` | `[x]` |
| P16 | CI | Moyenne | `pytest-cov>=4.0` ajouté ; CI génère un rapport de couverture | `[x]` |

### Améliorations et nouvelles fonctionnalités

| # | Module | Description | Statut |
|---|--------|-------------|--------|
| P9-WFP | `market` | `WFPDataBridgesClient` + `ExchangeRateClient` intégrés dans `Market` | `[x]` |
| P2 | `weather` | Alias `temperature_avg/mean` centralisé dans `_unifier_colonne_temperature()` | `[x]` |
| P10 | `kidas` | Clé de cache sécurisée par SHA-256 dans `execute()` | `[x]` |
| P11 | Infrastructure | `MODELS_DIR` documenté avec commentaire explicite dans `config.py` | `[x]` |
| P12 | Infrastructure | `EXCHANGE_RATES` dynamiques via `ExchangeRateClient` (TTL 24h, fallback) | `[x]` |
| P1 | `weather` | README mis à jour : comportement hybride CHIRPS/Open-Meteo décrit | `[x]` |
| P7 | `market` | `_portfolio_heuristique()` calcule le revenu réel (surface × rendement × prix) | `[x]` |
| P14 | Tests | Tests unitaires `kadi.cache` ajoutés (`tests/test_cache.py`) | `[x]` |
| P15 | Tests | Tests unitaires `kadi.config` ajoutés (`tests/test_config.py`) | `[x]` |

---

## Partie B — Autres tâches v1.1.0 (critiques, à traiter avant publication)

Ces points ont été découverts lors de l'audit approfondi du code source. Ils créent des
risques réels : faille de sécurité, données incorrectes ou incohérence visible pour l'utilisateur.
Aucun ne requiert une refonte architecturale. Chacun peut être traité en moins d'une heure.

---

### C1 — Incrémenter la version du package

**Module :** Infrastructure
**Fichier :** `pyproject.toml` ligne 11
**Sévérité :** Haute

**Problème :**
Le fichier déclare `version = "1.0.0"` alors que la branche s'appelle `v1.1.0` et que
toutes les corrections ont été livrées. Une publication PyPI avec cette version serait trompeuse.

**Action :**
```toml
version = "1.1.0"
```

**Statut : `[x]` Terminé**

---

### C2 - Retirer l'identifiant personnel de `config.py`

**Module :** Infrastructure
**Fichier :** `kadi/config.py` ligne ~264
**Sévérité :** Critique (sécurité)

**Problème :**
La variable `HAPI_APP_IDENTIFIER` contenait une valeur par défaut en base64 encodant
l'adresse personnelle `kadipy:delsdenla.dev@gmail.com`, exposant des données personnelles dans le dépôt public.

**Action effectuée :**
Remplacement de l'adresse personnelle par un identifiant générique de projet (`kadipy:requests@kadipy.com`, encodé en `a2FkaXB5OnJlcXVlc3RzQGthZGlweS5jb20=`). Cela permet d'interroger les données réelles de l'API HAPI HumData par défaut sans exposer de données personnelles.

**Statut : `[x]` Terminé**

---

### C3 — Corriger le stockage de `data_source` dans le cache SQLite

**Module :** `weather`
**Fichier :** `kadi/weather/data.py` ligne ~222
**Sévérité :** Haute (données incorrectes)

**Problème :**
Lors de la sauvegarde en cache SQLite, la colonne `data_source` est écrite en dur
comme `"mock_api"` pour toutes les données, quelle que soit leur vraie source
(CHIRPS, Open-Meteo, etc.). Les données CHIRPS historiques sont donc annotées
`"mock_api"` dans le cache, ce qui invalide toute analyse de provenance.

**Action :**
```python
# Extraire la source réelle depuis le DataFrame avant la sauvegarde
source_val = "open-meteo"
if "data_source" in data.columns:
    sources = data["data_source"].dropna().unique()
    if len(sources) > 0:
        source_val = str(sources[0])

# Utiliser source_val à la place de "mock_api" dans l'INSERT SQL
```

**Statut : `[ ]` À faire**

---

### C4 — Clarifier ou supprimer `data_ingestion.py`

**Module :** `market`
**Fichier :** `kadi/market/data_ingestion.py` (25 485 octets)
**Sévérité :** Moyenne (maintenabilité)

**Problème :**
Avec l'arrivée de `WFPDataBridgesClient`, ce fichier est probablement redondant.
Si des méthodes de `data_ingestion.py` sont encore appelées en parallèle du nouveau
client, il y a un risque de comportements dupliqués ou incohérents. Si le fichier
n'est plus importé, il alourdit inutilement le package.

**Action :**
1. Vérifier les imports dans tous les fichiers de `kadi/market/`.
2. Si `data_ingestion.py` n'est plus importé nulle part : le supprimer.
3. Sinon : documenter son rôle résiduel dans son en-tête avec une note explicite.

**Statut : `[ ]` À faire**

---

### C5 — Vérifier `soilgrids.py` et son intégration dans `hydrology.py`

**Module :** `weather`
**Fichier :** `kadi/_sources/soilgrids.py` (1 580 octets)
**Sévérité :** Haute (exactitude scientifique)

**Problème :**
`hydrology.py` appelle `fetch_soil_type(lat, lon)` pour déterminer automatiquement
le type de sol. Avec seulement 1 580 octets, l'implémentation est très légère pour
une source de données géospatiale. Si la fonction retourne une valeur statique ou
incorrecte, le bilan hydrique sera silencieusement erroné pour des localisations
dont le sol ne correspond pas au type retourné.

**Action :**
1. Lire `soilgrids.py` en entier.
2. Vérifier si l'appel à l'API SoilGrids est réel ou si c'est une valeur de repli statique.
3. Documenter le comportement dans la docstring de `Hydrology.__init__`.
4. Si l'API est réelle : ajouter un test d'intégration avec mock.

**Statut : `[ ]` À faire**

---

### C6 — Ajouter des tests pour le connecteur CHIRPS

**Module :** `weather`
**Fichier :** `kadi/_sources/chirps.py`
**Sévérité :** Haute (robustesse)

**Problème :**
`chirps.py` est la source de données la plus complexe du package (téléchargement
de rasters GeoTIFF, découpage spatial, cache de fichiers, gestion du délai de
15 jours). Aucun test dédié n'existe. Une régression dans la logique de découpage
ou de disponibilité des données passera silencieusement.

**Tests à créer dans `tests/weather/test_chirps.py` :**
- Test de `_chirps_disponible_pour()` : une date d'il y a 2 mois est disponible ;
  une date d'hier ne l'est pas.
- Test de `_construire_url()` : vérification du format de l'URL pour une date donnée.
- Test de `fetch_historical_precipitation()` avec un mock HTTP simulant un raster valide.

**Statut : `[ ]` À faire**

---

## Partie C — Tâches v1.2.0 (stratégiques, planifiées)

Ces points renforcent la valeur scientifique et l'adoption du package. Ils ne bloquent
pas le fonctionnement actuel.

---

### S1 — Activer Penman-Monteith dans le bilan hydrique

**Module :** `weather`
**Fichier :** `kadi/weather/hydrology.py`
**Horizon :** v1.2.0

**Contexte :**
La méthode `et0_fao56_penman()` est implémentée mais jamais appelée. Le bilan
hydrique utilise exclusivement Hargreaves-Samani. Pour les cultures sensibles au
déficit hydrique (riz, tomate), la différence peut atteindre 15 à 25% sur l'ETo
calculé. Open-Meteo fournit les variables nécessaires (humidité, vent, rayonnement).

**Action :**
Ajouter un paramètre `method='hargreaves'|'penman'` à `compute_water_balance()`.
Vérifier que le DataFrame retourné par `fetch_historical()` contient bien les
colonnes `humidity`, `wind_speed` et `solar_radiation`.

**Statut : `[~]` Reporté v1.2.0**

---

### S2 — Évaluer et améliorer le modèle de prévision de prix

**Module :** `market`
**Fichier :** `kadi/market/forecasting.py`
**Horizon :** v1.2.0 (évaluation + Prophet), v2.0.0 (LSTM)

**Contexte :**
Le modèle actuel (régression linéaire + harmoniques de Fourier) est solide. La
feuille de route mentionne Prophet et LSTM. Avant d'aller vers ces modèles, la
priorité est de calculer le MAPE réel du modèle actuel sur des données historiques
WFP disponibles et de publier ce chiffre dans la documentation. C'est la métrique
manquante depuis la v1.0.0.

**Actions :**
1. Calculer le MAPE réel sur des données WFP Bénin connues (backtesting).
2. Publier ce chiffre dans `docs/market/forecasting.md`.
3. Si le MAPE est supérieur à 20%, intégrer Prophet pour la v1.2.0.

**Statut : `[~]` Reporté v1.2.0**

---

### S3 — Publication de métriques de performance

**Module :** Documentation
**Fichier :** `benchmarks/performance_report.ipynb` (à créer)
**Horizon :** v1.1.1

**Contexte :**
Ni la documentation, ni les tests ne publient de métriques concrètes sur les
performances du package. Sans ces chiffres, KadiPy reste une démonstration de
concept, pas un outil validé utilisable dans un contexte académique ou institutionnel.

**Métriques à documenter :**
- MAPE du modèle de prévision de prix sur des données historiques WFP réelles.
- Temps de nettoyage d'un fichier de 10 000 lignes avec `DataPipeline`.
- Mémoire utilisée par le cache SQLite sur 5 ans de données CHIRPS.
- Temps de calcul du bilan hydrique sur une série de 3 650 jours.

**Statut : `[~]` Reporté v1.1.1**

---

### S4 — Connecteurs vers les données béninoises locales

**Module :** `_sources`
**Horizon :** v1.2.0 (si données accessibles) ou v2.0.0

**Contexte :**
KadiPy utilise exclusivement des sources internationales (Open-Meteo, CHIRPS,
HAPI HumData, OSRM). Les données du MAEP (Ministère de l'Agriculture, de l'Élevage
et de la Pêche) et de l'INSAE (Institut National de la Statistique) ne sont pas
intégrées. Un outil qui ignore les données officielles béninoises sera difficile à
légitimer auprès des institutions locales.

**Prochaine étape :**
Identifier si le MAEP ou l'INSAE exposent des données via une API publique ou un
portail de données ouvertes. Si oui, créer un connecteur sous forme de `DataSource`
kidas (`kadi/kidas/sources/maep_source.py`).

**Statut : `[~]` Reporté v1.2.0**

---

### S5 — Interface de visualisation ou notebook interactif

**Module :** Nouveau
**Horizon :** v1.2.0 (notebook), v2.0.0 (interface web)

**Contexte :**
KadiPy est une bibliothèque Python pure. Un conseiller agricole ou un technicien
de coopérative ne peut pas l'utiliser sans écrire du code. Pour l'adoption terrain,
une interface accessible est indispensable.

**Options :**
1. Notebook Jupyter interactif (`notebooks/exemple_saison_culturale.ipynb`) : rapide
   à produire, adapté à un public avec formation technique minimale.
2. Interface web légère : plus complexe mais utilisable sur mobile en zone agricole.

**Statut : `[~]` Reporté v1.2.0**

---

### S6 — Transport multimodal dans `logistics.py`

**Module :** `market`
**Fichier :** `kadi/market/logistics.py`
**Horizon :** v2.0.0

**Contexte :**
Le module couvre uniquement le transport routier via OSRM + Nominatim. Les cours
d'eau au Bénin (Ouémé, Mono, Couffo) sont utilisés pour le transport de cultures
dans certaines régions. À prioriser uniquement si des partenaires terrain expriment
ce besoin avec des données disponibles.

**Statut : `[~]` Reporté v2.0.0**

---

### S7 — Feuille de route datée dans `ROADMAP.md`

**Module :** Documentation
**Fichier :** `ROADMAP.md` (à créer à la racine du projet)
**Horizon :** Avant toute publication externe

**Contexte :**
La feuille de route ne contient pas de dates. Un contributeur externe ou un
partenaire ne peut pas s'organiser autour du planning de KadiPy.

**Contenu proposé pour `ROADMAP.md` :**

| Version | Périmètre | Échéance |
|---------|-----------|----------|
| v1.1.0 | Corrections v1.0.0 + API WFP DataBridges | Août 2026 |
| v1.1.1 | Corrections sécurité + benchmarks | Septembre 2026 |
| v1.2.0 | Penman-Monteith, MAEP, notebook interactif | Décembre 2026 |
| v2.0.0 | Prophet, interface web, transport multimodal | Juin 2027 |

**Statut : `[ ]` À faire**

---

## Tableau récapitulatif global

### Tâches v1.1.0 (toutes terminées)

| # | Module | Sévérité | Description courte | Statut |
|---|--------|----------|--------------------|--------|
| P8 | `kidas` | Critique | Rapport `execute()` aligné sur la documentation | `[x]` |
| P6 | `market` | Haute | `is_simulated` propagé depuis la vraie source | `[x]` |
| P13 | Infrastructure | Haute | `requirements.txt` réconcilié | `[x]` |
| P3 | `weather` | Haute | SPI via loi Gamma (McKee et al. 1993) | `[x]` |
| P4 | `market` | Haute | Bornes GPS lues depuis `CONFIG` | `[x]` |
| P9 | `kidas` | Haute | `fix_dates()` compteur corrigé | `[x]` |
| P5 | `market` | Moyenne | `get_market_functionality_index()` lève `NotImplementedError` | `[x]` |
| P16 | CI | Moyenne | `pytest-cov` ajouté + CI mise à jour | `[x]` |
| P9-WFP | `market` | N/A | API WFP DataBridges + taux de change dynamiques | `[x]` |
| P2 | `weather` | Faible | Alias `temperature_avg/mean` centralisé | `[x]` |
| P10 | `kidas` | Faible | Clé de cache SHA-256 | `[x]` |
| P11 | Infrastructure | Faible | `MODELS_DIR` documenté | `[x]` |
| P12 | Infrastructure | Moyenne | `EXCHANGE_RATES` dynamiques | `[x]` |
| P1 | `weather` | Moyenne | README mis à jour (CHIRPS/Open-Meteo) | `[x]` |
| P7 | `market` | Faible | `_portfolio_heuristique()` calcule un revenu réel | `[x]` |
| P14 | Tests | Moyenne | Tests `kadi.cache` ajoutés | `[x]` |
| P15 | Tests | Faible | Tests `kadi.config` ajoutés | `[x]` |

### Tâches v1.1.1 (critiques, à traiter avant publication)

| # | Module | Sévérité | Description courte | Statut |
|---|--------|----------|--------------------|--------|
| C1 | Infrastructure | Haute | Incrémenter la version à `1.1.0` dans `pyproject.toml` | `[x]` |
| C2 | Infrastructure | Critique | Retirer l'identifiant personnel de `config.py` | `[x]` |
| C3 | `weather` | Haute | Corriger `data_source` écrite `"mock_api"` dans le cache SQLite | `[ ]` |
| C4 | `market` | Moyenne | Clarifier ou supprimer `data_ingestion.py` | `[ ]` |
| C5 | `weather` | Haute | Vérifier `soilgrids.py` et documenter son comportement | `[ ]` |
| C6 | `weather` | Haute | Ajouter des tests pour le connecteur CHIRPS | `[ ]` |

### Tâches stratégiques (v1.2.0 et au-delà)

| # | Module | Description courte | Horizon | Statut |
|---|--------|--------------------|---------|--------|
| S1 | `weather` | Activer Penman-Monteith dans `compute_water_balance()` | v1.2.0 | `[~]` |
| S2 | `market` | Évaluer le MAPE réel + intégrer Prophet | v1.2.0 | `[~]` |
| S3 | Documentation | Publier métriques de performance dans un notebook | v1.1.1 | `[~]` |
| S4 | `_sources` | Connecteurs MAEP / INSAE | v1.2.0 | `[~]` |
| S5 | Nouveau | Notebook interactif pour utilisateurs terrain | v1.2.0 | `[~]` |
| S6 | `market` | Transport multimodal (fluvial) dans `logistics.py` | v2.0.0 | `[~]` |
| S7 | Documentation | Créer `ROADMAP.md` avec planning daté | Avant publication | `[ ]` |
