"""Load and shape CEPII BACI trade data into a bilateral edge list.

Raw BACI files are a manual, one-time download into ``data/raw/`` — see
``data/README.md``. Nothing here scrapes or downloads them.
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from . import config

_VERSION_RE = re.compile(r"_V(\d+)$")


def _version_tag(path: Path) -> int:
    """Extract the numeric BACI release tag from a filename stem."""
    match = _VERSION_RE.search(path.stem)
    if match is None:
        return -1
    return int(match.group(1))


def _newest(paths: list[Path]) -> Path:
    """Return the path with the highest ``_V*`` release tag."""
    return max(paths, key=_version_tag)


def _missing_file_error(pattern: str, raw_dir: Path) -> FileNotFoundError:
    """Build a FileNotFoundError naming ``pattern`` and pointing at the data README."""
    return FileNotFoundError(
        f"No files matching '{pattern}' in {raw_dir}. "
        "Download CEPII BACI (HS17) and copy the trade CSV plus "
        "country_codes / product_codes metadata into data/raw/ — "
        "see data/README.md for exact steps."
    )


def find_baci_files(
    raw_dir: Path = config.RAW_DIR,
    year: int = config.YEAR,
) -> dict[str, Path]:
    """Locate the BACI trade CSV and metadata CSVs for ``year`` in ``raw_dir``.

    Auto-detects the release/version tag by globbing. If files are missing, raise a
    ``FileNotFoundError`` whose message tells the user exactly what to download and
    where to put it (see ``data/README.md``). Never fabricate data.

    Returns:
        dict with keys ``"trade"``, ``"country_codes"``, ``"product_codes"`` → Path.
    """
    raw_dir = Path(raw_dir)
    patterns = {
        "trade": f"BACI_HS*_Y{year}_V*.csv",
        "country_codes": "country_codes_V*.csv",
        "product_codes": "product_codes_HS*_V*.csv",
    }
    result: dict[str, Path] = {}
    for key, pattern in patterns.items():
        matches = list(raw_dir.glob(pattern))
        if not matches:
            raise _missing_file_error(pattern, raw_dir)
        result[key] = _newest(matches)
    return result


def load_country_codes(path: Path | str) -> pd.DataFrame:
    """Load the BACI country dictionary → columns ``country_code``, ``iso3``, ``name``."""
    raw = pd.read_csv(path)
    required = ("country_code", "country_iso3", "country_name")
    missing = [c for c in required if c not in raw.columns]
    if missing:
        raise ValueError(f"country codes CSV missing columns {missing}: {path}")
    return pd.DataFrame(
        {
            "country_code": raw["country_code"].astype(int),
            "iso3": raw["country_iso3"].astype(str),
            "name": raw["country_name"].astype(str),
        }
    )


def load_baci(trade_path: Path | str) -> pd.DataFrame:
    """Load one year of BACI trade flows → columns ``t, i, j, k, v, q``."""
    trade = pd.read_csv(
        trade_path,
        dtype={"t": int, "i": int, "j": int, "k": str, "v": float, "q": float},
    )
    trade["k"] = trade["k"].str.zfill(6)
    return trade


def attach_iso3(trade: pd.DataFrame, country_codes: pd.DataFrame) -> pd.DataFrame:
    """Map numeric exporter ``i`` / importer ``j`` to ``exporter_iso3`` / ``importer_iso3``."""
    codes = country_codes[["country_code", "iso3"]]
    out = trade.merge(codes, left_on="i", right_on="country_code", how="left")
    out = out.rename(columns={"iso3": "exporter_iso3"}).drop(columns=["country_code"])
    out = out.merge(codes, left_on="j", right_on="country_code", how="left")
    out = out.rename(columns={"iso3": "importer_iso3"}).drop(columns=["country_code"])
    return out


def filter_countries(
    trade: pd.DataFrame,
    countries: list[str] = config.COUNTRIES,
) -> pd.DataFrame:
    """Keep only flows where both endpoints are in ``countries``."""
    mask = trade["exporter_iso3"].isin(countries) & trade["importer_iso3"].isin(countries)
    return trade.loc[mask].reset_index(drop=True)


def filter_products(trade: pd.DataFrame, hs_prefixes: list[str]) -> pd.DataFrame:
    """Keep only rows whose HS-6 code ``k`` starts with one of ``hs_prefixes``."""
    if not hs_prefixes:
        return trade.reset_index(drop=True)
    mask = trade["k"].str.startswith(tuple(hs_prefixes))
    return trade.loc[mask].reset_index(drop=True)


def _aggregate_edgelist(trade: pd.DataFrame) -> pd.DataFrame:
    """Sum product-level values into one edge per ordered pair; drop self-loops."""
    edges = trade.groupby(["exporter_iso3", "importer_iso3"], as_index=False).agg(
        value_kusd=("v", "sum")
    )
    edges = edges.loc[edges["exporter_iso3"] != edges["importer_iso3"]]
    return edges.reset_index(drop=True)


def build_edgelist(products: list[str] | None = None) -> pd.DataFrame:
    """Full pipeline → bilateral edge list.

    Runs find → load → attach ISO3 → filter countries → (optional product filter) →
    aggregate value over products.

    Args:
        products: HS prefixes to restrict to (e.g. ``config.HS_ENERGY``). ``None`` = all.

    Returns:
        DataFrame ``[exporter_iso3, importer_iso3, value_kusd]`` (one row per ordered pair).
    """
    paths = find_baci_files()
    trade = load_baci(paths["trade"])
    country_codes = load_country_codes(paths["country_codes"])
    trade = attach_iso3(trade, country_codes)
    trade = filter_countries(trade)
    if products is not None:
        trade = filter_products(trade, products)
    return _aggregate_edgelist(trade)
