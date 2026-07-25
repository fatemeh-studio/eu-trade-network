# Data — setup

How to get the raw files onto disk. For *what* the data is, why BACI was chosen, and the
caveats that matter when reading the results, see the **Data & method** page of the
[project site](https://fatemeh-studio.github.io/eu-trade-network/data.html).

## One-time download (manual)

The raw CEPII BACI CSVs are **not committed** — they are large, versioned, and covered by
an attribution licence. Download them once:

1. Go to the BACI page:
   **https://www.cepii.fr/CEPII/en/bdd_modele/bdd_modele_item.asp?id=37**
2. Download the **HS17** revision zip. It is one large `.zip` containing **all years** plus
   metadata. (The current release is `202601`; the loader auto-detects whichever version
   you have.)
3. Unzip and copy these three files into `data/raw/`:
   - `BACI_HS17_Y<YEAR>_V<REL>.csv` — the year set in `config.YEAR` (default 2022)
   - `country_codes_V<REL>.csv`
   - `product_codes_HS17_V<REL>.csv`

   `<REL>` is the release tag, e.g. `202601`. All three must share the same tag.

> The zip covers all years but you only need one year's CSV — delete the rest. Keep both
> metadata CSVs.

If a file is missing, `data_loader.find_baci_files` raises a `FileNotFoundError` naming the
pattern it could not match.

## Column dictionary (BACI trade CSV)

| col | meaning |
|-----|---------|
| `t` | year |
| `i` | exporter (numeric country code) |
| `j` | importer (numeric country code) |
| `k` | product (HS-6 code — keep as a string, leading zeros are significant) |
| `v` | trade value, **thousands of current USD** |
| `q` | quantity, metric tons (**missing in ~2% of rows** — not used) |

`country_codes_*.csv` maps numeric `country_code` → `country_name`, `country_iso3`.
Energy commodities (RQ4) are HS chapter **27**: `str(k).zfill(6)` starts with `"27"`.

## Directory layout

| path | committed? | contents |
|------|-----------|----------|
| `data/raw/` | no | the three BACI CSVs above |
| `data/processed/` | no | `trade.duckdb`, built by the notebooks |
| `data/external/` | no | scratch space |
| `data/reference/` | **yes** | `country_groups.csv` — the EU-27 + partner node set (ISO3, name, group) |

## Licence

**Etalab Open Licence 2.0** — any use permitted with attribution:

> Gaulier, G. & Zignago, S. (2010). *BACI: International Trade Database at the
> Product-Level*. CEPII Working Paper N°2010-23.
