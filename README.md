# European Trade Network

> Complex-systems analysis of European merchandise trade — **centrality**, **trade
> communities**, and **network resilience** — built from CEPII BACI open data.

![Bilateral merchandise trade flows between the EU-27 and eight major partners, 2022](figures/headline/01_flow_map.png)

**[→ Live report & notebooks](https://fatemeh-studio.github.io/eu-trade-network/)** —
findings, Data & method, executed analysis notebooks, and an interactive community
network.

## Findings (one line each)

- **RQ1.** Germany holds the network together (weighted betweenness 0.829); Austria is
  mid-tier by volume and not a bridge (betweenness = 0).
- **RQ2.** Three trade blocs emerge (Louvain Q ≈ 0.25) — drawn by geography and intensity,
  not EU membership.
- **RQ3.** The complete graph never fragments; on the backbone, targeted hub removal
  breaks it ~2.6× sooner than random failure, and three economies already hold half the
  trade value.
- **RQ4.** Energy (HS-27) is 12% of value but far more concentrated (top 3 ≈ 55% vs 38%) —
  bridge to [austria-energy-analysis](https://github.com/fatemeh-studio/austria-energy-analysis).

## Reproduce locally

```bash
conda env create -f environment.yml
conda activate eu-trade-network
pip install -e .
pre-commit install
nbstripout --install --attributes .gitattributes   # once per clone

# one-time BACI download → data/raw/  (see data/README.md)
jupyter lab   # run notebooks/01 → 05 top-to-bottom

# rebuild the site (optional; the live site is already published)
quarto render
# quarto publish gh-pages   # push _site to GitHub Pages
```

## Project structure

```
src/eu_trade_network/   analysis package
notebooks/              01 → 05 (rendered as pages on the site)
data.qmd · index.qmd    Quarto site: Data & method + Home
data/                   raw/ processed/ (gitignored) · reference/ (committed)
figures/headline/       committed PNGs
```

## Licence

Code: MIT (see `LICENSE`). Data: CEPII BACI under Etalab Open Licence 2.0 — attribution required.
