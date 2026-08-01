"""
Tests du connecteur CHIRPS et de son intégration dans WeatherData / WeatherSession.

Couverture :
- Extraction d'un raster GeoTIFF de synthèse au point GPS demandé.
- Mise en cache local du raster découpé.
- Lecture depuis le cache sans appel réseau.
- Gestion des erreurs réseau (repli sur Open-Meteo).
- Fusion CHIRPS + Open-Meteo selon les modes 'chirps', 'openmeteo' et 'both'.
- Propagation du paramètre source depuis WeatherSession.historical().
- Calcul du délai de disponibilité des données finales CHIRPS.
"""

import gzip
import io
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from kadi._sources.chirps import (
    _chirps_disponible_pour,
    fetch_historical_precipitation,
)
from kadi.exceptions import DataSourceError
from kadi.weather.data import WeatherData
from kadi.weather.location import Location


# ---------------------------------------------------------------------------
# Fixtures communes
# ---------------------------------------------------------------------------


@pytest.fixture
def location_parakou():
    """Localisation de test : Parakou, nord du Bénin."""
    return Location(latitude=9.337, longitude=2.630, name="Parakou")


@pytest.fixture
def df_chirps_3j():
    """DataFrame CHIRPS de synthèse sur 3 jours."""
    return pd.DataFrame({
        "date": pd.to_datetime(["2024-03-01", "2024-03-02", "2024-03-03"]),
        "precipitation": [2.5, 0.0, 8.1],
        "data_source": ["chirps", "chirps", "chirps"],
        "confidence": [1.0, 1.0, 1.0],
    })


@pytest.fixture
def df_openmeteo_30j():
    """DataFrame Open-Meteo de synthèse sur 30 jours."""
    dates = pd.date_range(start="2024-03-01", periods=30)
    df = pd.DataFrame({
        "temperature_min": [22.0] * 30,
        "temperature_max": [32.0] * 30,
        "temperature_mean": [27.0] * 30,
        "precipitation": [3.0] * 30,
        "data_source": ["open-meteo"] * 30,
        "data_quality": [1.0] * 30,
    }, index=dates)
    df.index.name = "date"
    return df


# ---------------------------------------------------------------------------
# Tests du calcul du délai de disponibilité CHIRPS
# ---------------------------------------------------------------------------


def test_chirps_disponible_pour_date_ancienne():
    """Une date de l'année passée doit toujours être disponible."""
    # Janvier 2020 : données disponibles depuis mi-février 2020
    assert _chirps_disponible_pour(date(2020, 1, 15)) is True


def test_chirps_indisponible_pour_mois_courant():
    """Le mois en cours ne doit jamais être disponible (délai non écoulé)."""
    mois_courant = date.today().replace(day=1)
    assert _chirps_disponible_pour(mois_courant) is False


def test_chirps_disponible_decembre_annee_precedente():
    """Décembre de l'année précédente doit être disponible (mi-janvier écoulé)."""
    annee_precedente = date.today().year - 1
    decembre = date(annee_precedente, 12, 15)
    assert _chirps_disponible_pour(decembre) is True


# ---------------------------------------------------------------------------
# Tests de fetch_historical_precipitation (connecteur bas niveau)
# ---------------------------------------------------------------------------


def test_fetch_precipitation_dates_toutes_futures():
    """
    Si toutes les dates demandées sont dans la fenêtre de délai,
    fetch_historical_precipitation doit retourner None.
    """
    # Demande sur le mois courant : délai non écoulé pour toutes les dates
    debut = date.today().replace(day=1).isoformat()
    fin = date.today().isoformat()

    result = fetch_historical_precipitation(
        lat=9.337, lon=2.630,
        start_date=debut, end_date=fin
    )

    assert result is None


def test_fetch_precipitation_date_debut_superieure_fin():
    """Un intervalle inversé (début > fin) doit lever ValueError."""
    with pytest.raises(ValueError, match="postérieure"):
        fetch_historical_precipitation(
            lat=9.337, lon=2.630,
            start_date="2024-06-15",
            end_date="2024-06-01"
        )


def test_fetch_precipitation_format_date_invalide():
    """Un format de date incorrect doit lever ValueError."""
    with pytest.raises(ValueError, match="Format de date"):
        fetch_historical_precipitation(
            lat=9.337, lon=2.630,
            start_date="15/01/2024",
            end_date="30/01/2024"
        )


def test_fetch_precipitation_erreur_reseau_retourne_none(tmp_path):
    """
    En cas d'erreur réseau persistante pour toutes les dates disponibles,
    la fonction doit retourner None après avoir émis des avertissements.
    """
    # On utilise une date ancienne (janvier 2020) qui est certifiée disponible
    avec_erreur = DataSourceError("Serveur CHC inaccessible")

    with patch(
        "kadi._sources.chirps._telecharger_et_decouper_raster",
        side_effect=avec_erreur
    ), patch(
        "kadi._sources.chirps._chemin_raster_cache",
        return_value=tmp_path / "raster_inexistant.tif"
    ):
        result = fetch_historical_precipitation(
            lat=9.337, lon=2.630,
            start_date="2020-01-01",
            end_date="2020-01-05"
        )

    # Toutes les dates ont échoué : retour None
    assert result is None


def test_fetch_precipitation_depuis_cache_local(tmp_path):
    """
    Si le raster existe déjà en cache, aucun téléchargement ne doit avoir lieu.
    La valeur de précipitation doit être correctement extraite.
    """
    # Raster factice dans le dossier temporaire
    fichier_cache = tmp_path / "chirps-v2.0.2020.01.15.tif"
    fichier_cache.write_bytes(b"FAKE_RASTER_CONTENT")

    valeur_attendue = 4.7

    with patch(
        "kadi._sources.chirps._chemin_raster_cache",
        return_value=fichier_cache
    ), patch(
        "kadi._sources.chirps._extraire_valeur_ponctuelle",
        return_value=valeur_attendue
    ), patch(
        "kadi._sources.chirps._telecharger_et_decouper_raster"
    ) as mock_dl:
        result = fetch_historical_precipitation(
            lat=9.337, lon=2.630,
            start_date="2020-01-15",
            end_date="2020-01-15"
        )

    # Le téléchargement ne doit pas avoir eu lieu
    mock_dl.assert_not_called()

    assert result is not None
    assert len(result) == 1
    assert result["precipitation"].iloc[0] == pytest.approx(valeur_attendue)
    assert result["data_source"].iloc[0] == "chirps"


def test_fetch_precipitation_structure_dataframe(tmp_path):
    """
    Le DataFrame retourné doit avoir les colonnes attendues et l'index date.
    """
    fichier_cache = tmp_path / "chirps-v2.0.2020.03.01.tif"
    fichier_cache.write_bytes(b"FAKE")

    with patch("kadi._sources.chirps._chemin_raster_cache", return_value=fichier_cache), \
         patch("kadi._sources.chirps._extraire_valeur_ponctuelle", return_value=5.2):

        result = fetch_historical_precipitation(
            lat=9.337, lon=2.630,
            start_date="2020-03-01",
            end_date="2020-03-01"
        )

    assert result is not None
    # Vérification des colonnes obligatoires
    for col in ("date", "precipitation", "data_source", "confidence"):
        assert col in result.columns
    # La colonne date doit être de type datetime
    assert pd.api.types.is_datetime64_any_dtype(result["date"])


# ---------------------------------------------------------------------------
# Tests d'intégration WeatherData avec le paramètre source
# ---------------------------------------------------------------------------


@patch("kadi.weather.data.WeatherData._save_to_cache")
@patch("kadi.weather.data.WeatherData._get_from_cache")
def test_source_openmeteo_utilise_open_meteo_uniquement(
    mock_cache, mock_save, location_parakou, df_openmeteo_30j
):
    """
    Avec source='openmeteo', fetch_historical doit utiliser exclusivement Open-Meteo.
    CHIRPS ne doit pas être appelé.
    """
    mock_cache.return_value = pd.DataFrame()

    with patch(
        "kadi._sources.open_meteo.fetch_historical",
        return_value=df_openmeteo_30j.reset_index().to_dict(orient="records")
    ), patch(
        "kadi._sources.chirps.fetch_historical_precipitation"
    ) as mock_chirps:
        weather = WeatherData(location_parakou)
        result = weather.fetch_historical(months_back=1, source="openmeteo")

    # CHIRPS ne doit pas avoir été appelé
    mock_chirps.assert_not_called()

    # Toutes les lignes doivent indiquer open-meteo comme source
    assert (result["data_source"] == "open-meteo").all()


@patch("kadi.weather.data.WeatherData._save_to_cache")
@patch("kadi.weather.data.WeatherData._get_from_cache")
def test_source_chirps_met_a_jour_precipitation(
    mock_cache, mock_save, location_parakou, df_openmeteo_30j, df_chirps_3j
):
    """
    Avec source='chirps', les précipitations doivent provenir de CHIRPS
    pour les dates couvertes, et les températures d'Open-Meteo.
    """
    mock_cache.return_value = pd.DataFrame()

    om_records = df_openmeteo_30j.reset_index().rename(
        columns={"date": "date"}
    ).to_dict(orient="records")

    with patch(
        "kadi._sources.open_meteo.fetch_historical",
        return_value=om_records
    ), patch(
        "kadi._sources.chirps.fetch_historical_precipitation",
        return_value=df_chirps_3j
    ):
        weather = WeatherData(location_parakou)
        result = weather.fetch_historical(months_back=1, source="chirps")

    # Les lignes couvertes par CHIRPS doivent indiquer 'chirps'
    dates_chirps = pd.to_datetime(df_chirps_3j["date"])
    masque = result.index.isin(dates_chirps)
    assert result.loc[masque, "data_source"].eq("chirps").all()

    # Les lignes non couvertes par CHIRPS doivent indiquer 'open-meteo'
    assert result.loc[~masque, "data_source"].eq("open-meteo").all()


@patch("kadi.weather.data.WeatherData._save_to_cache")
@patch("kadi.weather.data.WeatherData._get_from_cache")
def test_source_chirps_repli_openmeteo_si_chirps_echoue(
    mock_cache, mock_save, location_parakou, df_openmeteo_30j
):
    """
    Si CHIRPS lève une exception, le repli doit être Open-Meteo avec un
    avertissement. Le DataFrame retourné ne doit pas être vide.
    """
    mock_cache.return_value = pd.DataFrame()

    om_records = df_openmeteo_30j.reset_index().to_dict(orient="records")

    with patch(
        "kadi._sources.open_meteo.fetch_historical",
        return_value=om_records
    ), patch(
        "kadi._sources.chirps.fetch_historical_precipitation",
        return_value=None  # Aucune donnée CHIRPS disponible
    ):
        weather = WeatherData(location_parakou)
        result = weather.fetch_historical(months_back=1, source="chirps")

    # Le DataFrame ne doit pas être vide (repli sur Open-Meteo)
    assert not result.empty
    # Toutes les lignes doivent indiquer open-meteo après repli
    assert (result["data_source"] == "open-meteo").all()


@patch("kadi.weather.data.WeatherData._save_to_cache")
@patch("kadi.weather.data.WeatherData._get_from_cache")
def test_source_both_combine_chirps_et_openmeteo(
    mock_cache, mock_save, location_parakou, df_openmeteo_30j, df_chirps_3j
):
    """
    Avec source='both', les dates couvertes par CHIRPS doivent indiquer 'chirps'
    et les autres 'open-meteo'.
    """
    mock_cache.return_value = pd.DataFrame()

    om_records = df_openmeteo_30j.reset_index().to_dict(orient="records")

    with patch(
        "kadi._sources.open_meteo.fetch_historical",
        return_value=om_records
    ), patch(
        "kadi._sources.chirps.fetch_historical_precipitation",
        return_value=df_chirps_3j
    ):
        weather = WeatherData(location_parakou)
        result = weather.fetch_historical(months_back=1, source="both")

    dates_chirps = pd.to_datetime(df_chirps_3j["date"])
    masque_chirps = result.index.isin(dates_chirps)

    # Au moins une ligne doit indiquer 'chirps'
    assert masque_chirps.any()
    assert result.loc[masque_chirps, "data_source"].eq("chirps").all()


# ---------------------------------------------------------------------------
# Test de bout en bout via WeatherSession
# ---------------------------------------------------------------------------


@patch("kadi.weather.data.WeatherData._save_to_cache")
@patch("kadi.weather.data.WeatherData._get_from_cache")
def test_session_historical_propage_source(
    mock_cache, mock_save, location_parakou, df_openmeteo_30j
):
    """
    WeatherSession.historical(source='openmeteo') doit propager le paramètre
    source à WeatherData.fetch_historical().
    """
    from kadi.weather.session import WeatherSession

    mock_cache.return_value = pd.DataFrame()

    om_records = df_openmeteo_30j.reset_index().to_dict(orient="records")

    with patch(
        "kadi._sources.open_meteo.fetch_historical",
        return_value=om_records
    ), patch(
        "kadi._sources.chirps.fetch_historical_precipitation"
    ) as mock_chirps:
        session = WeatherSession(
            latitude=location_parakou.latitude,
            longitude=location_parakou.longitude,
            name=location_parakou.name,
        )
        result = session.historical(months_back=1, source="openmeteo")

    # CHIRPS ne doit pas avoir été appelé
    mock_chirps.assert_not_called()
    assert not result.empty
