"""Smoke tests — pass at bootstrap, before any analysis code is written."""

import csv
import importlib

import eu_trade_network
from eu_trade_network import config


def test_version():
    assert eu_trade_network.__version__ == "0.1.0"


def test_country_sets():
    assert len(config.EU27) == 27
    assert "AUT" in config.EU27
    assert len(config.COUNTRIES) == len(set(config.COUNTRIES))  # no duplicates
    assert len(config.COUNTRIES) == len(config.EU27) + len(config.PARTNERS)


def test_year_and_seed():
    assert isinstance(config.YEAR, int)
    assert isinstance(config.RANDOM_SEED, int)


def test_all_modules_import():
    for mod in (
        "data_loader",
        "graph",
        "metrics",
        "communities",
        "resilience",
        "energy",
        "db",
        "viz",
    ):
        importlib.import_module(f"eu_trade_network.{mod}")


def test_reference_matches_config():
    with config.COUNTRY_GROUPS_CSV.open() as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == len(config.COUNTRIES)
    assert {r["iso3"] for r in rows} == set(config.COUNTRIES)
