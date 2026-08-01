"""
Script de préparation de l'environnement hors ligne pour KadiPy.

Ce script pré-télécharge et découpe les rasters CHIRPS sur l'emprise du Bénin
pour une ou plusieurs années, constituant ainsi un cache local qui permet un
usage sans connexion Internet. Il prépare également le cache SoilGrids.

Usage :
    source .kadi_venv/bin/activate
    python scripts/setup_offline_data.py              # Télécharge l'année courante
    python scripts/setup_offline_data.py 2024         # Télécharge une année précise
    python scripts/setup_offline_data.py 2022 2026    # Télécharge une plage d'années
"""

import json
import logging
import sys
from datetime import date, timedelta
from pathlib import Path

# Configuration du journal pour afficher les messages en console
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def ensure_cache_dir(cache_dir: Path) -> None:
    """
    Crée le dossier de cache principal s'il n'existe pas.

    :param cache_dir: Chemin vers le dossier de cache à créer.
    """
    cache_dir.mkdir(parents=True, exist_ok=True)
    logger.info("Dossier de cache assuré : %s", cache_dir)


def prefetch_chirps_benin(annee: int) -> None:
    """
    Pré-télécharge et découpe les rasters CHIRPS africa_daily sur l'emprise
    du Bénin pour une année complète.

    Les rasters découpés sont sauvegardés dans le dossier de cache CHIRPS
    configuré dans CONFIG["weather"]["chirps"]["raster_cache_dir"].
    La bbox utilisée est lue depuis CONFIG["weather"]["gps_validation_bbox"]
    afin d'être synchronisée avec la validation GPS du reste du package.

    Seules les dates pour lesquelles les données CHIRPS finales sont
    disponibles (délai ~15 jours après la fin du mois) sont téléchargées.

    :param annee: Année civile à pré-charger (ex: 2024).
    """
    # Import différé pour ne pas bloquer si le package n'est pas installé
    try:
        from kadi.config import CONFIG
        from kadi._sources.chirps import (
            _chirps_disponible_pour,
            _chemin_raster_cache,
            _telecharger_et_decouper_raster,
        )
    except ImportError as exc:
        logger.error(
            "Impossible d'importer kadi. Vérifiez que le venv est activé "
            "et que KadiPy est installé (pip install -e .). Détail : %s", exc
        )
        return

    logger.info("Démarrage du pré-téléchargement CHIRPS pour l'année %d...", annee)

    # Bornes de la plage annuelle
    debut = date(annee, 1, 1)
    fin = date(annee, 12, 31)

    # On ne dépasse pas aujourd'hui
    fin = min(fin, date.today())

    nb_total = 0
    nb_telecharges = 0
    nb_deja_en_cache = 0
    nb_ignores_delai = 0
    nb_erreurs = 0

    jour = debut
    while jour <= fin:
        nb_total += 1

        # Vérification du délai de disponibilité des données finales CHIRPS
        if not _chirps_disponible_pour(jour):
            nb_ignores_delai += 1
            jour += timedelta(days=1)
            continue

        chemin = _chemin_raster_cache(jour)

        # Lecture depuis le cache local si le raster existe déjà
        if chemin.exists():
            nb_deja_en_cache += 1
            jour += timedelta(days=1)
            continue

        # Téléchargement, découpage et sauvegarde du raster
        try:
            _telecharger_et_decouper_raster(jour, chemin)
            nb_telecharges += 1
            logger.info("  [OK] %s", jour.isoformat())
        except Exception as exc:
            nb_erreurs += 1
            logger.warning("  [ERREUR] %s : %s", jour.isoformat(), exc)

        jour += timedelta(days=1)

    # Rapport de fin de traitement
    logger.info(
        "Pré-téléchargement CHIRPS %d terminé : %d jours traités, "
        "%d téléchargés, %d déjà en cache, %d ignorés (délai), %d erreurs.",
        annee, nb_total, nb_telecharges, nb_deja_en_cache, nb_ignores_delai, nb_erreurs
    )


def setup_soilgrids_cache(cache_dir: Path) -> None:
    """
    Crée un fichier de cache SoilGrids de référence pour les points clés du Bénin.

    :param cache_dir: Chemin vers le dossier de cache principal.
    """
    soil_file = cache_dir / "soilgrids_cache.json"
    if soil_file.exists():
        logger.info("Fichier cache SoilGrids existant. Ignoré.")
        return

    logger.info("Création du cache SoilGrids (points de référence du Bénin)...")

    # Points de référence géographiques du Bénin avec leur type de sol dominant
    points_reference = [
        {"lat": 6.36536, "lon": 2.41833, "soil_type": "sableux"},       # Cotonou
        {"lat": 7.18286, "lon": 1.99119, "soil_type": "ferrallitique"}, # Abomey
        {"lat": 9.33716, "lon": 2.63031, "soil_type": "ferrugineux"},   # Parakou
        {"lat": 10.30416, "lon": 1.37962, "soil_type": "limoneux"},     # Natitingou
    ]

    with open(soil_file, "w", encoding="utf-8") as fichier:
        json.dump(points_reference, fichier, indent=4, ensure_ascii=False)

    logger.info("Fichier cache SoilGrids créé : %s", soil_file)


if __name__ == "__main__":
    # Lecture des arguments : années à pré-charger (défaut : année courante)
    args = sys.argv[1:]
    annees_a_charger = []

    if len(args) == 0:
        # Pas d'argument : on pré-charge uniquement l'année courante
        annees_a_charger = [date.today().year]
    elif len(args) == 1:
        # Un argument : une année précise
        annees_a_charger = [int(args[0])]
    elif len(args) == 2:
        # Deux arguments : une plage d'années (inclusive)
        debut_annee = int(args[0])
        fin_annee = int(args[1])
        annees_a_charger = list(range(debut_annee, fin_annee + 1))
    else:
        logger.error(
            "Usage : python setup_offline_data.py [annee_debut] [annee_fin]"
        )
        sys.exit(1)

    # Dossier de cache principal (~/.kadi)
    cache_dir_principal = Path.home() / ".kadi"
    ensure_cache_dir(cache_dir_principal)

    # Pré-chargement des rasters CHIRPS pour chaque année demandée
    for annee in annees_a_charger:
        prefetch_chirps_benin(annee)

    # Mise en place du cache SoilGrids
    setup_soilgrids_cache(cache_dir_principal)

    logger.info("Configuration hors ligne terminée avec succès.")
