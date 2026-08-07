"""
Tests unitaires pour le module kadi._sources.exchange_client.

Vérifie le comportement de ExchangeRateClient :
- la structure du dictionnaire retourné,
- la logique d'inversion des taux,
- le mécanisme de cache TTL,
- le fallback sur config.EXCHANGE_RATES en cas d'erreur réseau.
"""

import time
from unittest.mock import MagicMock, patch

import pytest

from kadi._sources.exchange_client import ExchangeRateClient
from kadi.config import EXCHANGE_RATES


# Réponse JSON simulée de l'API Frankfurter pour XOF/USD
_REPONSE_USD = {
    "date": "2026-07-31",
    "base": "XOF",
    "quote": "USD",
    "rate": 0.00175,
}

# Réponse JSON simulée de l'API Frankfurter pour XOF/EUR
_REPONSE_EUR = {
    "date": "2026-07-31",
    "base": "XOF",
    "quote": "EUR",
    "rate": 0.00152,
}


def _creer_reponse_mock(donnees: dict, status_code: int = 200) -> MagicMock:
    """
    Crée un objet mock simulant une réponse de requests.get.

    Args:
        donnees (dict): Données JSON de la réponse simulée.
        status_code (int): Code HTTP de la réponse.

    Returns:
        MagicMock: Mock compatible avec l'interface requests.Response.
    """
    mock_reponse = MagicMock()
    mock_reponse.status_code = status_code
    mock_reponse.json.return_value = donnees
    # raise_for_status ne fait rien pour les codes 2xx
    mock_reponse.raise_for_status.return_value = None
    return mock_reponse


class TestGetRatesStructure:
    """Vérifie la structure du dictionnaire retourné par get_rates()."""

    def test_get_rates_retourne_dict_avec_cles_attendues(self):
        """get_rates() doit retourner un dict avec les clés USD_TO_XOF et EUR_TO_XOF."""
        # Simulation de deux appels successifs (un par devise)
        reponses = [
            _creer_reponse_mock(_REPONSE_USD),
            _creer_reponse_mock(_REPONSE_EUR),
        ]

        with patch("kadi._sources.exchange_client.requests.get", side_effect=reponses):
            client = ExchangeRateClient()
            taux = client.get_rates()

        # Vérification des clés présentes
        assert "USD_TO_XOF" in taux
        assert "EUR_TO_XOF" in taux

    def test_get_rates_retourne_uniquement_floats(self):
        """Les valeurs du dictionnaire doivent être des nombres flottants."""
        reponses = [
            _creer_reponse_mock(_REPONSE_USD),
            _creer_reponse_mock(_REPONSE_EUR),
        ]

        with patch("kadi._sources.exchange_client.requests.get", side_effect=reponses):
            client = ExchangeRateClient()
            taux = client.get_rates()

        assert isinstance(taux["USD_TO_XOF"], float)
        assert isinstance(taux["EUR_TO_XOF"], float)


class TestInversionTaux:
    """Vérifie la logique d'inversion du taux XOF/devise -> devise/XOF."""

    def test_taux_usd_est_inverse_du_taux_xof(self):
        """USD_TO_XOF doit être l'inverse du taux XOF/USD retourné par Frankfurter."""
        reponses = [
            _creer_reponse_mock(_REPONSE_USD),
            _creer_reponse_mock(_REPONSE_EUR),
        ]

        with patch("kadi._sources.exchange_client.requests.get", side_effect=reponses):
            client = ExchangeRateClient()
            taux = client.get_rates()

        # 1 / 0.00175 ≈ 571.43
        taux_attendu = round(1.0 / _REPONSE_USD["rate"], 4)
        assert abs(taux["USD_TO_XOF"] - taux_attendu) < 0.01

    def test_taux_eur_est_inverse_du_taux_xof(self):
        """EUR_TO_XOF doit être l'inverse du taux XOF/EUR retourné par Frankfurter."""
        reponses = [
            _creer_reponse_mock(_REPONSE_USD),
            _creer_reponse_mock(_REPONSE_EUR),
        ]

        with patch("kadi._sources.exchange_client.requests.get", side_effect=reponses):
            client = ExchangeRateClient()
            taux = client.get_rates()

        # 1 / 0.00152 ≈ 657.89
        taux_attendu = round(1.0 / _REPONSE_EUR["rate"], 4)
        assert abs(taux["EUR_TO_XOF"] - taux_attendu) < 0.01

    def test_taux_usd_superieur_a_zero(self):
        """USD_TO_XOF doit être strictement positif."""
        reponses = [
            _creer_reponse_mock(_REPONSE_USD),
            _creer_reponse_mock(_REPONSE_EUR),
        ]

        with patch("kadi._sources.exchange_client.requests.get", side_effect=reponses):
            client = ExchangeRateClient()
            taux = client.get_rates()

        assert taux["USD_TO_XOF"] > 0


class TestFallbackHorsLigne:
    """Vérifie le comportement en mode hors ligne (absence de réseau)."""

    def test_fallback_si_connection_error(self):
        """
        En cas de ConnectionError, get_rates() doit retourner config.EXCHANGE_RATES.
        """
        import requests

        with patch(
            "kadi._sources.exchange_client.requests.get",
            side_effect=requests.exceptions.ConnectionError("Pas de réseau"),
        ):
            client = ExchangeRateClient()
            taux = client.get_rates()

        # Doit retourner les taux de repli de config.py
        assert taux["USD_TO_XOF"] == EXCHANGE_RATES["USD_TO_XOF"]
        assert taux["EUR_TO_XOF"] == EXCHANGE_RATES["EUR_TO_XOF"]

    def test_fallback_si_timeout(self):
        """
        En cas de Timeout, get_rates() doit retourner config.EXCHANGE_RATES.
        """
        import requests

        with patch(
            "kadi._sources.exchange_client.requests.get",
            side_effect=requests.exceptions.Timeout("Timeout"),
        ):
            client = ExchangeRateClient()
            taux = client.get_rates()

        assert taux["USD_TO_XOF"] == EXCHANGE_RATES["USD_TO_XOF"]

    def test_fallback_contient_les_deux_cles(self):
        """Le dictionnaire de fallback doit aussi avoir les deux clés attendues."""
        import requests

        with patch(
            "kadi._sources.exchange_client.requests.get",
            side_effect=requests.exceptions.ConnectionError,
        ):
            client = ExchangeRateClient()
            taux = client.get_rates()

        assert "USD_TO_XOF" in taux
        assert "EUR_TO_XOF" in taux


class TestCacheTTL:
    """Vérifie que le cache mémoire évite les appels HTTP redondants."""

    def test_cache_ttl_evite_double_appel_http(self):
        """Deux appels successifs à get_rates() ne doivent produire qu'un seul appel HTTP."""
        reponses = [
            _creer_reponse_mock(_REPONSE_USD),
            _creer_reponse_mock(_REPONSE_EUR),
        ]

        with patch(
            "kadi._sources.exchange_client.requests.get", side_effect=reponses
        ) as mock_get:
            client = ExchangeRateClient(ttl_secondes=60)

            # Premier appel : déclenche les requêtes HTTP
            client.get_rates()

            # Deuxième appel : doit lire depuis le cache
            client.get_rates()

            # requests.get doit avoir été appelé exactement 2 fois (une par devise)
            assert mock_get.call_count == 2

    def test_cache_expire_apres_ttl(self):
        """Une fois le TTL expiré, le prochain appel doit interroger l'API."""
        reponses_tour_1 = [
            _creer_reponse_mock(_REPONSE_USD),
            _creer_reponse_mock(_REPONSE_EUR),
        ]
        reponses_tour_2 = [
            _creer_reponse_mock(_REPONSE_USD),
            _creer_reponse_mock(_REPONSE_EUR),
        ]

        with patch(
            "kadi._sources.exchange_client.requests.get",
            side_effect=reponses_tour_1 + reponses_tour_2,
        ) as mock_get:
            # TTL très court : 0 seconde (cache expire immédiatement)
            client = ExchangeRateClient(ttl_secondes=0)

            client.get_rates()
            # Simulation du passage du temps
            time.sleep(0.01)
            client.get_rates()

            # Les deux tours ont déclenché des appels HTTP (4 au total : 2 par tour)
            assert mock_get.call_count == 4
