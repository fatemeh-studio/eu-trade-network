"""Central configuration: paths, analysis year, and the country node set.

Import from here everywhere. Never hard-code paths or country lists in notebooks.
"""

from pathlib import Path

# --- Paths -----------------------------------------------------------------
PROJECT_ROOT: Path = Path(__file__).resolve().parents[2]
DATA_DIR: Path = PROJECT_ROOT / "data"
RAW_DIR: Path = DATA_DIR / "raw"
PROCESSED_DIR: Path = DATA_DIR / "processed"
REFERENCE_DIR: Path = DATA_DIR / "reference"
FIGURES_DIR: Path = PROJECT_ROOT / "figures"
HEADLINE_FIG_DIR: Path = FIGURES_DIR / "headline"
QA_FIG_DIR: Path = FIGURES_DIR / "qa"
SQL_DIR: Path = PROJECT_ROOT / "sql"
DB_PATH: Path = PROCESSED_DIR / "trade.duckdb"
COUNTRY_GROUPS_CSV: Path = REFERENCE_DIR / "country_groups.csv"

# --- Analysis parameters ---------------------------------------------------
# BACI trade year to analyse. 2022 is definitive; bump to 2023 once you trust the
# latest release (the most recent BACI year can still be revised).
YEAR: int = 2022

# HS chapter(s) counted as energy commodities for RQ4 (mineral fuels & oils).
HS_ENERGY: list[str] = ["27"]

RANDOM_SEED: int = 42

# Disparity-filter significance level for backbone extraction (RQ2).
DISPARITY_ALPHA: float = 0.05

# --- Node set: EU-27 + major partners (~35 economies) ----------------------
EU27: list[str] = [
    "AUT",
    "BEL",
    "BGR",
    "HRV",
    "CYP",
    "CZE",
    "DNK",
    "EST",
    "FIN",
    "FRA",
    "DEU",
    "GRC",
    "HUN",
    "IRL",
    "ITA",
    "LVA",
    "LTU",
    "LUX",
    "MLT",
    "NLD",
    "POL",
    "PRT",
    "ROU",
    "SVK",
    "SVN",
    "ESP",
    "SWE",
]

# Edit this list freely to reshape the network. Note 2022 Russia trade is
# distorted by sanctions — drop RUS if you want a cleaner structural snapshot.
PARTNERS: list[str] = ["GBR", "CHE", "NOR", "USA", "CHN", "TUR", "RUS", "JPN"]

COUNTRIES: list[str] = EU27 + PARTNERS
