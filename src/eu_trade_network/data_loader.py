"""Load and shape CEPII BACI trade data into a bilateral edge list.

Raw BACI files are a manual, one-time download into ``data/raw/`` — see
``data/README.md``. Nothing here scrapes or downloads them.
"""

import pandas as pd

from . import config


def find_baci_files(raw_dir=config.RAW_DIR, year=config.YEAR):
    """Locate the BACI trade CSV and metadata CSVs for ``year`` in ``raw_dir``.

    Auto-detects the release/version tag by globbing. If files are missing, raise a
    ``FileNotFoundError`` whose message tells the user exactly what to download and
    where to put it (see ``data/README.md``). Never fabricate data.

    Returns:
        dict with keys ``"trade"``, ``"country_codes"``, ``"product_codes"`` → Path.
    """
    raise NotImplementedError("TODO: implement in Cursor Prompt P1")


def load_country_codes(path) -> pd.DataFrame:
    """Load the BACI country dictionary → columns ``country_code``, ``iso3``, ``name``."""
    raise NotImplementedError("TODO: implement in Cursor Prompt P1")


def load_baci(trade_path) -> pd.DataFrame:
    """Load one year of BACI trade flows → columns ``t, i, j, k, v, q``."""
    raise NotImplementedError("TODO: implement in Cursor Prompt P1")


def attach_iso3(trade: pd.DataFrame, country_codes: pd.DataFrame) -> pd.DataFrame:
    """Map numeric exporter ``i`` / importer ``j`` to ``exporter_iso3`` / ``importer_iso3``."""
    raise NotImplementedError("TODO: implement in Cursor Prompt P1")


def filter_countries(trade: pd.DataFrame, countries=config.COUNTRIES) -> pd.DataFrame:
    """Keep only flows where both endpoints are in ``countries``."""
    raise NotImplementedError("TODO: implement in Cursor Prompt P1")


def filter_products(trade: pd.DataFrame, hs_prefixes: list[str]) -> pd.DataFrame:
    """Keep only rows whose HS-6 code ``k`` starts with one of ``hs_prefixes``."""
    raise NotImplementedError("TODO: implement in Cursor Prompt P1")


def build_edgelist(products: list[str] | None = None) -> pd.DataFrame:
    """Full pipeline → bilateral edge list.

    Runs find → load → attach ISO3 → filter countries → (optional product filter) →
    aggregate value over products.

    Args:
        products: HS prefixes to restrict to (e.g. ``config.HS_ENERGY``). ``None`` = all.

    Returns:
        DataFrame ``[exporter_iso3, importer_iso3, value_kusd]`` (one row per ordered pair).
    """
    raise NotImplementedError("TODO: implement in Cursor Prompt P1")
