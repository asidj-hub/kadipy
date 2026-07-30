# Suivi des tâches — KadiPy v1.1.0

**Source :** `analyse/analyse_1.0.0.md` — analyse du 25 juillet 2026

**Branche :** `v1.1.0`

**Légende :**
- `[x]` Terminé
- `[-]` En cours
- `[ ]` À faire
- `[~]` Reporté (v1.2.0 ou ultérieure)

---

## Priorité 1 — Corrections bloquantes pour la v1.1.0

### P1 — Bug critique : rapport de `execute()` incohérent avec la documentation

**Problème 8** | Module `kadi.kidas` | Sévérité : **Critique**

**Statut : `[x]` Résolu**

La structure du dictionnaire retourné par `DataPipeline.execute()` ne correspondait pas à la documentation.
Le code a été aligné sur le format canonique documenté (`nb_rows_in`, `nb_rows_out`, `steps_summary`, `quality_score`, `warnings`, `cache_utilise`, `details`).

**Fichiers modifiés :**
- `kadi/kidas/pipeline.py`
- `docs/kidas/index.md`, `docs/kidas/pipeline.md`
- `tests/test_kidas/test_processing.py`

---

### P2 — `storage_vs_sell_now()` force `is_simulated=True` sur des données réelles

**Problème 6** | Module `kadi.market` | Sévérité : **Haute**

**Statut : `[x]` Résolu**

La ligne `est_simule = True` qui écrasait le flag réel a été remplacée par
`est_simule = prevision.get("is_simulated", True)`. Le flag est maintenant propagé
depuis `predict_price()`. La valeur par défaut `True` est conservée si la clé est
absente, pour ne pas casser le comportement offline.

**Fichiers modifiés :**
- `kadi/market/decision_support.py` (ligne ~324)
- `docs/market/decision_support.md` (description du champ `is_simulated`)

**Action :**
```python
# Avant (incorrect)
est_simule = True  # Le module forecasting V1 reste un stub
# Après (correct)
est_simule = prevision.get("is_simulated", True)
```

**Fichier :** `kadi/market/decision_support.py` (ligne ~324)

---

### P3 — `requirements.txt` désynchronisé avec `pyproject.toml`

**Problème 13** | Infrastructure | Sévérité : **Haute**

**Statut : `[x]` Résolu**

`requirements.txt` a été réécrit comme un alias vers `pyproject.toml` (une seule ligne
`-e ".[dev]"`), ce qui élimine la désynchronisation à la source. `xlrd<2.0` a été
ajouté dans les dépendances optionnelles de `pyproject.toml` sous l'extra `[xls]`.
`dask` a été retiré (non importé dans le code de production).

**Fichiers modifiés :**
- `requirements.txt` (réécrit)
- `pyproject.toml` (ajout de l'extra `xls`)

---

### P4 — SPI approximé par Z-score au lieu d'une loi Gamma

**Problème 3** | Module `kadi.weather` | Sévérité : **Haute**

**Statut : `[x]` Résolu**

La méthode `spi()` dans `risk.py` utilisait une approximation Z-score pour
calculer l'indice SPI. Elle a été remplacée par la méthode standard de
McKee et al. (1993) :

1. Ajustement d'une loi Gamma sur les cumuls non nuls via
   `scipy.stats.gamma.fit(valid_data, floc=0)`.
2. Application d'une correction de masse de probabilité pour les jours
   sans pluie (cumul nul).
3. Conversion en score SPI via `scipy.stats.norm.ppf`.

La signature publique de `spi()` est inchangée. La méthode lève maintenant
`InsufficientData` si le nombre de cumuls non nuls est inférieur à 10.

**Fichiers modifiés :**
- `kadi/weather/risk.py` (méthode `spi()`, lignes 62-153)
- `tests/weather/test_risk.py` (nouveaux tests: signe du SPI, cas limites Gamma)

---

### P5 — Bornes GPS du module `market` dupliquées en dur

**Problème 4** | Module `kadi.market` | Sévérité : **Haute**

**Statut : `[x]` Résolu**

Les constantes `_LAT_MIN`, `_LAT_MAX`, `_LON_MIN`, `_LON_MAX` étaient
définies en dur dans `market/__init__.py` avec des valeurs différentes de
celles de `config.py` (incohérence réelle : `min_lat` valait 6.0 au lieu de
2.5, `min_lon` valait 0.5 au lieu de -1.5). Elles sont maintenant lues
depuis `CONFIG["weather"]["gps_validation_bbox"]` avec des valeurs de repli.

**Action réalisée :**
```python
from kadi.config import CONFIG

_bbox = CONFIG.get("weather", {}).get("gps_validation_bbox", {})
_LAT_MIN = _bbox.get("min_lat", 2.5)
_LAT_MAX = _bbox.get("max_lat", 12.5)
_LON_MIN = _bbox.get("min_lon", -1.5)
_LON_MAX = _bbox.get("max_lon", 4.0)
```

**Fichiers modifiés :**
- `kadi/market/__init__.py` (lignes 21-30)
- `tests/test_market/test_market_components.py` (ajout de
  `test_market_bornes_gps_issues_de_config`, mise à jour commentaires)

---

### P6 — `fix_dates()` accumule un mauvais compteur de dates corrigées

**Problème 9** | Module `kadi.kidas` | Sévérité : **Haute**

**Statut : `[ ]` À faire**

Dans `cleaner.py` lignes 362-363, `nb_corrigees` est calculé mais jamais utilisé. Le rapport accumule `nb_avant` au lieu du nombre réel de dates converties.

**Action :**
```python
# Avant (incorrect)
nb_corrigees = int(nb_avant - (nb_avant - nb_apres))  # toujours = nb_apres
nb_dates_corrigees += nb_avant                         # mauvais compteur
# Après (correct)
nb_corrigees = int(nb_apres)
nb_dates_corrigees += nb_corrigees
```

**Fichier :** `kadi/kidas/cleaner.py` (lignes ~362-363)

---

### P7 — `get_market_functionality_index()` retourne toujours 7.9

**Problème 5** | Module `kadi.market` | Sévérité : **Moyenne**

**Statut : `[ ]` À faire**

Dans `data_ingestion.py`, la méthode retourne `7.9` en dur sans aucun calcul. Elle est exposée publiquement sans utilité concrète.

**Action :** lever une `NotImplementedError` explicite :
```python
def get_market_functionality_index(self, market_id: str) -> float:
    raise NotImplementedError(
        "get_market_functionality_index() n'est pas encore implémentée. "
        "Elle sera disponible après intégration de la source FEWSNET."
    )
```

**Fichier :** `kadi/market/data_ingestion.py` (ligne ~615)

---

### P8 — Pas de rapport de couverture `pytest-cov` dans la CI

**Problème 16** | CI / GitHub Actions | Sévérité : **Moyenne**

**Statut : `[ ]` À faire**

Aucun rapport de couverture n'est généré dans le workflow CI. Impossible de détecter une régression de couverture.

**Action :** ajouter dans `.github/workflows/` :
```yaml
- name: Lancer les tests avec couverture
  run: |
    pytest tests/ --cov=kadi --cov-report=xml --cov-report=term-missing
```

Seuil minimal recommandé : `--cov-fail-under=70`

**Fichier :** `.github/workflows/*.yml`

---

### P9 — Intégration transparente de l'API WFP DataBridges (nouvelle fonctionnalité v1.1.0)

**Nouvelle fonctionnalité** | Module `kadi.market` | Sévérité : N/A

**Statut : `[ ]` À faire**

Dans la v1.1.0, l'API WFP DataBridges sera intégrée directement. L'utilisateur n'aura pas à injecter une clé API personnelle. Le client gérera automatiquement l'accès aux endpoints publics ou via un jeton par défaut embarqué.

---

## Priorité 2 — Améliorations pour la v1.2.0 ou ultérieure

| # | Problème | Module | Sévérité | Description courte | Statut |
|---|---------|--------|----------|--------------------|--------|
| 2 | `weather` | `weather` | Faible | Alias `temperature_avg/mean` dupliqué dans plusieurs fichiers | `[~]` |
| 10 | `kidas` | `kidas` | Faible | Clé de cache non hachée dans `execute()` (risque de collision) | `[~]` |
| 11 | `config` | Infrastructure | Faible | `MODELS_DIR` pointe vers `kadi/_ml/` qui n'existe pas | `[~]` |
| 12 | `config` | Infrastructure | Moyenne | `EXCHANGE_RATES` statiques, mise à jour prévue non implémentée | `[~]` |
| 1 | `weather` | `weather` | Moyenne | CHIRPS annoncé dans le README mais désactivé sans mention | `[~]` |
| 7 | `market` | `market` | Faible | Valeur magique `1_500_000` codée en dur dans `_portfolio_heuristique()` | `[~]` |
| 14 | `tests` | Tests | Moyenne | `kadi.cache` non testé directement (manque fixtures `tmp_path`) | `[~]` |
| 15 | `tests` | Tests | Faible | `kadi.config` non testé (variables d'environnement non vérifiées) | `[~]` |

---

## Tableau récapitulatif global

| # | Module | Sévérité | Description courte | Statut |
|---|--------|----------|--------------------|--------|
| 8 | `kidas` | Critique | Rapport `execute()` incohérent avec la documentation | `[x]` |
| 6 | `market` | Haute | `storage_vs_sell_now()` force `is_simulated=True` | `[x]` |
| 13 | `config` | Haute | `requirements.txt` désynchronisé avec `pyproject.toml` | `[x]` |
| 3 | `weather` | Haute | SPI approximé par Z-score au lieu d'une loi Gamma | `[x]` |
| 4 | `market` | Haute | Bornes GPS dupliquées en dur au lieu de lire `CONFIG` | `[x]` |
| 9 | `kidas` | Haute | `nb_dates_corrigees` calculé incorrectement dans `fix_dates()` | `[ ]` |
| 5 | `market` | Moyenne | `get_market_functionality_index()` retourne toujours 7.9 | `[ ]` |
| 16 | CI | Moyenne | Pas de rapport `pytest-cov` dans la CI | `[ ]` |
| — | `market` | N/A | Intégration API WFP DataBridges (v1.1.0) | `[ ]` |
| 2 | `weather` | Faible | Alias `temperature_avg/mean` dupliqué | `[~]` |
| 10 | `kidas` | Faible | Clé de cache non sécurisée dans `execute()` | `[~]` |
| 11 | `config` | Faible | `MODELS_DIR` pointe vers un dossier inexistant | `[~]` |
| 12 | `config` | Moyenne | `EXCHANGE_RATES` statiques sans mise à jour | `[~]` |
| 1 | `weather` | Moyenne | CHIRPS annoncé mais désactivé sans mention dans le README | `[~]` |
| 7 | `market` | Faible | Valeur magique `1_500_000` dans `_portfolio_heuristique()` | `[~]` |
| 14 | `tests` | Moyenne | `kadi.cache` non testé directement | `[~]` |
| 15 | `tests` | Faible | `kadi.config` non testé | `[~]` |
