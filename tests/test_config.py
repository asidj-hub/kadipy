# -*- coding: utf-8 -*-
"""
Tests unitaires pour le module kadi.config.

Ce module vérifie que la configuration par défaut est cohérente, que toutes
les clés attendues sont présentes, et que les variables d'environnement
surchargent correctement les valeurs au moment de l'import.
"""

import importlib

import pytest

import kadi.config as config_module
from kadi.config import (
    CACHE_DB,
    CACHE_DIR,
    CONFIG,
    EXCHANGE_RATES,
    LOG_DIR,
    LOG_FILE,
    MODELS_DIR,
    OPENMETEO_API_URL,
    CHIRPS_BASE_URL,
    HAPI_APP_IDENTIFIER,
    HAPI_API_URL,
    FRANKFURTER_API_URL,
)


# ---------------------------------------------------------------------------
# Tests de structure de CONFIG
# ---------------------------------------------------------------------------

class TestConfigStructure:
    """Vérifie la présence et la cohérence des clés de CONFIG."""

    def test_config_contient_cle_weather(self):
        """CONFIG doit contenir la section 'weather'."""
        assert "weather" in CONFIG, "Clé 'weather' manquante dans CONFIG."

    def test_config_contient_cle_market(self):
        """CONFIG doit contenir la section 'market'."""
        assert "market" in CONFIG, "Clé 'market' manquante dans CONFIG."

    def test_config_contient_cle_logistics(self):
        """CONFIG doit contenir la section 'logistics'."""
        assert "logistics" in CONFIG, "Clé 'logistics' manquante dans CONFIG."

    def test_config_contient_cle_kidas(self):
        """CONFIG doit contenir la section 'kidas'."""
        assert "kidas" in CONFIG, "Clé 'kidas' manquante dans CONFIG."

    def test_config_weather_gps_validation_bbox_present(self):
        """CONFIG['weather'] doit contenir une clé 'gps_validation_bbox'."""
        assert "gps_validation_bbox" in CONFIG["weather"], (
            "Clé 'gps_validation_bbox' manquante dans CONFIG['weather']."
        )

    def test_config_weather_gps_bbox_min_lat_inferieur_max_lat(self):
        """La bbox météo doit avoir min_lat strictement inférieur à max_lat."""
        bbox = CONFIG["weather"]["gps_validation_bbox"]
        assert bbox["min_lat"] < bbox["max_lat"], (
            f"Incohérence GPS : min_lat={bbox['min_lat']} >= max_lat={bbox['max_lat']}."
        )

    def test_config_weather_gps_bbox_min_lon_inferieur_max_lon(self):
        """La bbox météo doit avoir min_lon strictement inférieur à max_lon."""
        bbox = CONFIG["weather"]["gps_validation_bbox"]
        assert bbox["min_lon"] < bbox["max_lon"], (
            f"Incohérence GPS : min_lon={bbox['min_lon']} >= max_lon={bbox['max_lon']}."
        )

    def test_config_weather_chirps_source_default_valide(self):
        """CONFIG['weather']['chirps']['source_default'] doit être une valeur attendue."""
        # Valeurs acceptées par fetch_historical()
        valeurs_valides = {"chirps", "openmeteo", "both"}
        source = CONFIG["weather"]["chirps"]["source_default"]
        assert source in valeurs_valides, (
            f"source_default='{source}' non reconnu. Valeurs attendues : {valeurs_valides}."
        )

    def test_config_market_min_history_weeks_positif(self):
        """CONFIG['market']['min_history_weeks'] doit être un entier positif."""
        valeur = CONFIG["market"]["min_history_weeks"]
        assert isinstance(valeur, int) and valeur > 0, (
            f"min_history_weeks doit être un entier positif, obtenu : {valeur}."
        )

    def test_config_logistics_gamma_route_superieur_a_un(self):
        """Le coefficient gamma_route doit être >= 1 (route au mieux parfaite)."""
        gamma = CONFIG["logistics"]["gamma_route"]
        assert gamma >= 1.0, (
            f"gamma_route={gamma} est inférieur à 1.0 (impossible physiquement)."
        )

    def test_config_kidas_max_file_size_mb_positif(self):
        """CONFIG['kidas']['max_file_size_mb'] doit être un nombre positif."""
        valeur = CONFIG["kidas"]["max_file_size_mb"]
        assert valeur > 0, (
            f"max_file_size_mb doit être positif, obtenu : {valeur}."
        )


# ---------------------------------------------------------------------------
# Tests des chemins et répertoires
# ---------------------------------------------------------------------------

class TestConfigChemins:
    """Vérifie la cohérence des chemins définis dans config.py."""

    def test_cache_dir_existe(self):
        """CACHE_DIR doit exister après l'import du module (créé automatiquement)."""
        assert CACHE_DIR.exists(), (
            f"CACHE_DIR n'existe pas : {CACHE_DIR}."
        )

    def test_log_dir_existe(self):
        """LOG_DIR doit exister après l'import du module."""
        assert LOG_DIR.exists(), (
            f"LOG_DIR n'existe pas : {LOG_DIR}."
        )

    def test_cache_db_dans_cache_dir(self):
        """CACHE_DB doit être un enfant direct de CACHE_DIR."""
        assert CACHE_DB.parent == CACHE_DIR, (
            f"CACHE_DB ({CACHE_DB}) n'est pas dans CACHE_DIR ({CACHE_DIR})."
        )

    def test_log_file_dans_log_dir(self):
        """LOG_FILE doit être un enfant direct de LOG_DIR."""
        assert LOG_FILE.parent == LOG_DIR, (
            f"LOG_FILE ({LOG_FILE}) n'est pas dans LOG_DIR ({LOG_DIR})."
        )

    def test_models_dir_est_une_instance_path(self):
        """MODELS_DIR doit être un objet Path (même si le dossier n'existe pas encore)."""
        from pathlib import Path
        assert isinstance(MODELS_DIR, Path), (
            f"MODELS_DIR doit être un Path, obtenu : {type(MODELS_DIR)}."
        )


# ---------------------------------------------------------------------------
# Tests des taux de change
# ---------------------------------------------------------------------------

class TestExchangeRates:
    """Vérifie la cohérence des taux de change de repli."""

    def test_exchange_rates_contient_usd_to_xof(self):
        """EXCHANGE_RATES doit contenir la clé 'USD_TO_XOF'."""
        assert "USD_TO_XOF" in EXCHANGE_RATES, (
            "Clé 'USD_TO_XOF' manquante dans EXCHANGE_RATES."
        )

    def test_exchange_rates_contient_eur_to_xof(self):
        """EXCHANGE_RATES doit contenir la clé 'EUR_TO_XOF'."""
        assert "EUR_TO_XOF" in EXCHANGE_RATES, (
            "Clé 'EUR_TO_XOF' manquante dans EXCHANGE_RATES."
        )

    def test_exchange_rates_valeurs_positives(self):
        """Les taux de change doivent être des nombres strictement positifs."""
        for cle, valeur in EXCHANGE_RATES.items():
            assert isinstance(valeur, (int, float)) and valeur > 0, (
                f"Taux '{cle}' doit être un nombre positif, obtenu : {valeur}."
            )

    def test_eur_xof_proche_taux_fixe_uemoa(self):
        """Le taux EUR/XOF doit être proche du taux fixe UEMOA (655.957)."""
        taux = EXCHANGE_RATES["EUR_TO_XOF"]
        # On accepte une légère variation autour du taux fixe
        assert abs(taux - 655.957) < 1.0, (
            f"EUR_TO_XOF={taux} s'écarte trop du taux fixe UEMOA (655.957)."
        )


# ---------------------------------------------------------------------------
# Tests de surcharge par variables d'environnement
# ---------------------------------------------------------------------------

class TestSurchargeEnvVars:
    """Vérifie que les variables d'environnement surchargent les URL par défaut."""

    def test_openmeteo_api_url_peut_etre_surchargee(self, monkeypatch):
        """OPENMETEO_API_URL doit refléter la variable d'environnement si définie."""
        # Définition de la variable d'environnement avant le rechargement du module
        monkeypatch.setenv("OPENMETEO_API_URL", "http://localhost:9999/meteo")

        # Rechargement du module pour relire os.environ
        importlib.reload(config_module)

        assert config_module.OPENMETEO_API_URL == "http://localhost:9999/meteo", (
            "OPENMETEO_API_URL n'a pas pris en compte la variable d'environnement."
        )

    def test_chirps_base_url_peut_etre_surchargee(self, monkeypatch):
        """CHIRPS_BASE_URL doit refléter la variable d'environnement si définie."""
        monkeypatch.setenv("CHIRPS_BASE_URL", "http://localhost:8888/chirps")

        importlib.reload(config_module)

        assert config_module.CHIRPS_BASE_URL == "http://localhost:8888/chirps", (
            "CHIRPS_BASE_URL n'a pas pris en compte la variable d'environnement."
        )

    def test_hapi_app_identifier_peut_etre_surcharge(self, monkeypatch):
        """HAPI_APP_IDENTIFIER doit refléter la variable d'environnement si définie."""
        monkeypatch.setenv("HAPI_APP_IDENTIFIER", "mon_identifiant_test_123")

        importlib.reload(config_module)

        assert config_module.HAPI_APP_IDENTIFIER == "mon_identifiant_test_123", (
            "HAPI_APP_IDENTIFIER n'a pas pris en compte la variable d'environnement."
        )

    def test_hapi_api_url_peut_etre_surchargee(self, monkeypatch):
        """HAPI_API_URL doit refléter la variable d'environnement si définie."""
        monkeypatch.setenv("HAPI_API_URL", "http://localhost:7777/hapi")

        importlib.reload(config_module)

        assert config_module.HAPI_API_URL == "http://localhost:7777/hapi", (
            "HAPI_API_URL n'a pas pris en compte la variable d'environnement."
        )

    def test_frankfurter_api_url_peut_etre_surchargee(self, monkeypatch):
        """FRANKFURTER_API_URL doit refléter la variable d'environnement si définie."""
        monkeypatch.setenv("FRANKFURTER_API_URL", "http://localhost:6666/fx")

        importlib.reload(config_module)

        assert config_module.FRANKFURTER_API_URL == "http://localhost:6666/fx", (
            "FRANKFURTER_API_URL n'a pas pris en compte la variable d'environnement."
        )
