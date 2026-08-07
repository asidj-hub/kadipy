# -*- coding: utf-8 -*-
"""
Tests unitaires pour le module kadi.cache.

Ce module vérifie le bon fonctionnement de get_connection() et init_db(),
socle du mode offline-first de KadiPy. Tous les tests utilisent une base
SQLite temporaire via tmp_path pour ne pas polluer le cache réel de l'utilisateur.
"""

import sqlite3

import pytest

# Import du module à tester
import kadi.cache as cache_module
from kadi.cache import get_connection, init_db
from kadi.exceptions import CacheError


# ---------------------------------------------------------------------------
# Fixture centrale : base de données SQLite temporaire
# ---------------------------------------------------------------------------

@pytest.fixture
def cache_temporaire(tmp_path, monkeypatch):
    """Redirige CACHE_DB et cache_module.CACHE_DB vers une base temporaire.

    Remplace le chemin de base de données réel par un fichier isolé dans
    tmp_path, de sorte que chaque test parte d'une base vierge et ne
    modifie jamais le cache réel de l'utilisateur.

    Args:
        tmp_path (Path): Répertoire temporaire fourni par pytest.
        monkeypatch (MonkeyPatch): Fixture pytest pour les substitutions.

    Yields:
        Path: Chemin vers la base SQLite temporaire.
    """
    # Chemin de la base temporaire isolée par test
    chemin_db_temp = tmp_path / "test_cache.db"

    # Substitution dans les deux endroits où CACHE_DB est lu
    monkeypatch.setattr(cache_module, "CACHE_DB", chemin_db_temp)

    # Import local de kadi.config pour patcher aussi la source d'origine
    import kadi.config as config_module
    monkeypatch.setattr(config_module, "CACHE_DB", chemin_db_temp)

    yield chemin_db_temp


# ---------------------------------------------------------------------------
# Tests de init_db()
# ---------------------------------------------------------------------------

class TestInitDb:
    """Vérifie le comportement de la fonction init_db()."""

    def test_init_db_cree_weather_data(self, cache_temporaire):
        """init_db() doit créer la table weather_data."""
        # Initialisation de la base sur le chemin temporaire
        init_db()

        # Vérification directe via sqlite3
        conn = sqlite3.connect(cache_temporaire)
        curseur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='weather_data';"
        )
        assert curseur.fetchone() is not None, "La table weather_data est absente."
        conn.close()

    def test_init_db_cree_market_prices(self, cache_temporaire):
        """init_db() doit créer la table market_prices."""
        init_db()

        conn = sqlite3.connect(cache_temporaire)
        curseur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='market_prices';"
        )
        assert curseur.fetchone() is not None, "La table market_prices est absente."
        conn.close()

    def test_init_db_cree_cache_metadata(self, cache_temporaire):
        """init_db() doit créer la table cache_metadata."""
        init_db()

        conn = sqlite3.connect(cache_temporaire)
        curseur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='cache_metadata';"
        )
        assert curseur.fetchone() is not None, "La table cache_metadata est absente."
        conn.close()

    def test_init_db_cree_price_predictions(self, cache_temporaire):
        """init_db() doit créer la table price_predictions."""
        init_db()

        conn = sqlite3.connect(cache_temporaire)
        curseur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='price_predictions';"
        )
        assert curseur.fetchone() is not None, "La table price_predictions est absente."
        conn.close()

    def test_init_db_idempotent(self, cache_temporaire):
        """Appeler init_db() deux fois de suite ne doit pas lever d'exception.

        Les requêtes CREATE TABLE IF NOT EXISTS garantissent l'idempotence.
        """
        # Premier appel
        init_db()
        # Second appel : ne doit pas planter
        init_db()

    def test_init_db_cree_les_index(self, cache_temporaire):
        """init_db() doit créer au moins les index de base."""
        init_db()

        conn = sqlite3.connect(cache_temporaire)
        curseur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index';"
        )
        index_noms = {ligne[0] for ligne in curseur.fetchall()}
        conn.close()

        # Index attendus définis dans cache.py
        attendus = {
            "idx_location_date",
            "idx_crop_market_date",
            "idx_last_fetch",
        }
        for idx in attendus:
            assert idx in index_noms, f"Index attendu manquant : {idx}"


# ---------------------------------------------------------------------------
# Tests de get_connection()
# ---------------------------------------------------------------------------

class TestGetConnection:
    """Vérifie le comportement de la fonction get_connection()."""

    def test_get_connection_retourne_connexion_valide(self, cache_temporaire):
        """get_connection() doit retourner une connexion SQLite fonctionnelle."""
        # Initialisation préalable de la base
        init_db()

        # La connexion doit s'établir sans lever d'exception
        conn = get_connection()
        assert conn is not None

        # Vérification d'une requête simple
        curseur = conn.execute("SELECT 1;")
        assert curseur.fetchone()[0] == 1
        conn.close()

    def test_get_connection_row_factory_active(self, cache_temporaire):
        """get_connection() doit activer la row_factory sqlite3.Row."""
        init_db()

        conn = get_connection()
        # sqlite3.Row permet l'accès par nom de colonne
        assert conn.row_factory == sqlite3.Row
        conn.close()

    def test_get_connection_comme_context_manager(self, cache_temporaire):
        """get_connection() utilisée avec 'with' ne doit pas laisser de verrou ouvert."""
        init_db()

        # Utilisation comme gestionnaire de contexte
        with get_connection() as conn:
            curseur = conn.execute("SELECT 1;")
            assert curseur.fetchone()[0] == 1

        # Après le bloc, une nouvelle connexion doit pouvoir s'ouvrir sans blocage
        with get_connection() as conn2:
            assert conn2 is not None

    def test_get_connection_leve_cache_error_si_chemin_invalide(self, monkeypatch):
        """get_connection() doit lever CacheError si le chemin est inaccessible.

        On simule l'échec en remplaçant sqlite3.connect par une fonction
        qui lève systématiquement une sqlite3.Error.
        """
        # Remplacement de sqlite3.connect par un stub défaillant
        def connect_defaillant(*args, **kwargs):
            """Simule une erreur de connexion SQLite."""
            raise sqlite3.Error("Chemin inaccessible (simulation test)")

        monkeypatch.setattr(sqlite3, "connect", connect_defaillant)

        # get_connection() doit convertir l'erreur en CacheError
        with pytest.raises(CacheError, match="Impossible de se connecter"):
            get_connection()


# ---------------------------------------------------------------------------
# Tests d'intégration légère : écriture et lecture
# ---------------------------------------------------------------------------

class TestCacheEcritureLecture:
    """Tests d'intégration : vérifie qu'on peut écrire et relire des données."""

    def test_ecriture_lecture_cache_metadata(self, cache_temporaire):
        """Insérer une ligne dans cache_metadata et la relire doit fonctionner."""
        init_db()

        with get_connection() as conn:
            # Insertion d'une entrée de métadonnées
            conn.execute(
                """
                INSERT INTO cache_metadata
                    (module_name, table_name, data_source, last_fetch)
                VALUES ('weather', 'weather_data', 'open-meteo', '2026-01-01T12:00:00')
                ON CONFLICT(module_name, data_source) DO NOTHING;
                """
            )
            conn.commit()

            # Relecture de l'entrée insérée
            curseur = conn.execute(
                "SELECT module_name, data_source FROM cache_metadata LIMIT 1;"
            )
            ligne = curseur.fetchone()

        assert ligne is not None
        assert ligne[0] == "weather"
        assert ligne[1] == "open-meteo"

    def test_ecriture_lecture_weather_data(self, cache_temporaire):
        """Insérer une ligne dans weather_data et la relire doit fonctionner."""
        init_db()

        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO weather_data
                    (location_id, latitude, longitude, date, hour,
                     temperature_min, temperature_max, temperature_avg,
                     precipitation, data_type, data_source, confidence, fetched_at)
                VALUES
                    ('Parakou', 9.33, 2.63, '2026-01-01', -1,
                     18.0, 32.0, 25.0, 0.0, 'historical', 'test', 1.0,
                     '2026-01-01T12:00:00');
                """
            )
            conn.commit()

            curseur = conn.execute(
                "SELECT location_id, temperature_avg FROM weather_data LIMIT 1;"
            )
            ligne = curseur.fetchone()

        assert ligne is not None
        assert ligne[0] == "Parakou"
        assert ligne[1] == pytest.approx(25.0)
