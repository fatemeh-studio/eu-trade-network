# Data

## Primary source — CEPII BACI (manual, one-time download)

BACI is CEPII's harmonised bilateral trade database, built from UN Comtrade with the
mirror-flow discrepancies reconciled. It is the academic standard for trade-network work
and needs **no API key** — unlike the UN Comtrade API, which now requires registration and
has row limits on the free tier.

### Steps
1. Go to the BACI page: **https://www.cepii.fr/CEPII/en/bdd_modele/bdd_modele_item.asp?id=37**
2. Download the **HS17** revision zip (latest HS revision). It is one large `.zip`
   containing **all years** plus metadata. (The current release is `202601`; the loader
   auto-detects whichever version you have.)
3. Unzip and copy these three files into `data/raw/`:
   - `BACI_HS17_Y<YEAR>_V<REL>.csv`  — the year you set in `config.YEAR` (default 2022)
   - `country_codes_V<REL>.csv`
   - `product_codes_HS17_V<REL>.csv`
   (`<REL>` is the release tag, e.g. `202601`.)

> The full zip is large (all years). You only need one year's CSV in `data/raw/`; you can
> delete the others. Keep the two metadata CSVs.

### Column dictionary (BACI trade CSV)
| col | meaning |
|-----|---------|
| `t` | year |
| `i` | exporter (numeric country code) |
| `j` | importer (numeric country code) |
| `k` | product (HS-6 code) |
| `v` | trade value, **thousands of current USD** |
| `q` | quantity, metric tons (**missing in ~2% of rows** — do not rely on it) |

`country_codes_*.csv` maps the numeric `country_code` → `country_name`, `country_iso3`.
Energy commodities (RQ4) = HS chapter **27** (mineral fuels/oils): `str(k).zfill(6)` starts
with `"27"`.

### Citation / licence
Licence: **Etalab Open Licence 2.0** — any use permitted with attribution. Cite:
Gaulier, G. & Zignago, S. (2010), *BACI: International Trade Database at the Product-Level*,
CEPII Working Paper N°2010-23. (This is why raw files are gitignored — redistribute by
pointing to CEPII, not by committing the data.)

## What is committed
- `data/reference/country_groups.csv` — the EU-27 + partner set used as network nodes,
  with ISO3, name, and group. This is the only committed dataset.

## Alternatives (not used, for reference)
- **UN Comtrade Plus** (`comtradeapicall`): needs a free API key; the free tier caps rows
  per call, so full bilateral matrices need many calls. Good for small targeted pulls.
- **Eurostat Comext** (via the `eurostat` package): EU-reporter-centric, so extra-EU↔extra-EU
  flows are limited — weaker for a symmetric multi-country network.
