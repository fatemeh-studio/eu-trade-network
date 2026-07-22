"""Unit tests for the BACI data loader — synthetic frames only, no real CSVs."""

import pandas as pd
import pytest

from eu_trade_network.data_loader import (
    _aggregate_edgelist,
    attach_iso3,
    filter_countries,
    filter_products,
)


@pytest.fixture
def country_codes() -> pd.DataFrame:
    """Tiny BACI-style country dictionary."""
    return pd.DataFrame(
        {
            "country_code": [276, 40, 250, 840],
            "iso3": ["DEU", "AUT", "FRA", "USA"],
            "name": ["Germany", "Austria", "France", "United States"],
        }
    )


@pytest.fixture
def trade_flows() -> pd.DataFrame:
    """Synthetic product-level BACI rows (numeric i/j, HS-6 ``k``, value ``v``)."""
    return pd.DataFrame(
        {
            "t": [2022, 2022, 2022, 2022, 2022, 2022],
            "i": [276, 276, 276, 250, 40, 840],
            "j": [40, 40, 250, 40, 40, 276],
            "k": ["270900", "271000", "870323", "270900", "010121", "270900"],
            "v": [10.0, 5.0, 2.0, 3.0, 1.0, 8.0],
            "q": [1.0, 0.5, 0.1, 0.3, 0.01, 0.8],
        }
    )


def test_attach_iso3(trade_flows: pd.DataFrame, country_codes: pd.DataFrame) -> None:
    out = attach_iso3(trade_flows, country_codes)
    assert list(out["exporter_iso3"]) == ["DEU", "DEU", "DEU", "FRA", "AUT", "USA"]
    assert list(out["importer_iso3"]) == ["AUT", "AUT", "FRA", "AUT", "AUT", "DEU"]


def test_filter_countries_both_endpoints(
    trade_flows: pd.DataFrame,
    country_codes: pd.DataFrame,
) -> None:
    attached = attach_iso3(trade_flows, country_codes)
    # Exclude USA — the USA→DEU row must drop; AUT self-loop stays until aggregation.
    filtered = filter_countries(attached, countries=["DEU", "AUT", "FRA"])
    assert set(filtered["exporter_iso3"]).issubset({"DEU", "AUT", "FRA"})
    assert set(filtered["importer_iso3"]).issubset({"DEU", "AUT", "FRA"})
    assert "USA" not in set(filtered["exporter_iso3"])
    assert len(filtered) == 5


def test_filter_products(trade_flows: pd.DataFrame) -> None:
    energy = filter_products(trade_flows, hs_prefixes=["27"])
    assert len(energy) == 4
    assert energy["k"].str.startswith("27").all()

    animals = filter_products(trade_flows, hs_prefixes=["01"])
    assert list(animals["k"]) == ["010121"]


def test_aggregate_sums_duplicate_product_rows(
    trade_flows: pd.DataFrame,
    country_codes: pd.DataFrame,
) -> None:
    attached = attach_iso3(trade_flows, country_codes)
    # Two DEU→AUT product rows (10 + 5) must become one edge with value 15.
    edges = _aggregate_edgelist(attached)
    deu_aut = edges.loc[
        (edges["exporter_iso3"] == "DEU") & (edges["importer_iso3"] == "AUT"),
        "value_kusd",
    ]
    assert len(deu_aut) == 1
    assert deu_aut.iloc[0] == pytest.approx(15.0)

    # Self-loop AUT→AUT dropped.
    assert not ((edges["exporter_iso3"] == "AUT") & (edges["importer_iso3"] == "AUT")).any()

    assert list(edges.columns) == ["exporter_iso3", "importer_iso3", "value_kusd"]
