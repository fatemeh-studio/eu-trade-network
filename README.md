# European Trade Network

> Complex-systems analysis of European merchandise trade — **centrality**, **trade
> communities**, and **network resilience** — built from CEPII BACI open data.

![Bilateral merchandise trade flows between the EU-27 and eight major partners, 2022](figures/headline/01_flow_map.png)

[![Live site](https://img.shields.io/badge/site-GitHub%20Pages-1f6feb)](https://fatemeh-studio.github.io/eu-trade-network/)

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

# register a Jupyter kernel for this env (optional)
python -m ipykernel install --user --name eu-trade-network

# one-time BACI download → data/raw/  (see data/README.md)
jupyter lab   # run notebooks/01 → 05 top-to-bottom

# preview the site locally (replays _freeze/, no notebook run, no BACI needed)
quarto preview
```

## Publishing

**Push to `main`. That is the whole workflow** — [`.github/workflows/publish.yml`](.github/workflows/publish.yml)
renders the site and pushes it to `gh-pages`, which GitHub Pages serves. Never render or
commit onto `gh-pages` by hand.

CI does not run the notebooks. It replays `_freeze/`, the committed cache of cell
outputs, which exists because nbstripout strips outputs out of the `.ipynb` files on
commit. So `_freeze/` — and `network_viz/`, the PyVis graph built by NB03 — **are
committed on purpose**; they are the only record of the results.

The one rule that follows: **after changing notebook code or prose, refresh the freeze in
the same commit.**

```bash
quarto render --execute                 # re-runs notebooks; needs BACI in data/raw/
git add _freeze network_viz && git commit -m "refresh freeze"
```

Forget it and the publish job fails with a missing-kernel error rather than quietly
serving the old output — `execute.freeze` is set to `auto`, not `true`, precisely so
that mistake is loud. Editing only `.qmd` prose or `styles/` needs no refresh.


## Project structure

```
src/eu_trade_network/   analysis package
notebooks/              01 → 05 (rendered as pages on the site)
data.qmd · index.qmd    Quarto site: Data & method + Home
data/                   raw/ processed/ (gitignored) · reference/ (committed)
figures/headline/       committed PNGs
_freeze/                committed notebook outputs — the site renders from these
network_viz/            committed PyVis graph, built by NB03
```

## Licence

Code: MIT (see `LICENSE`). Data: CEPII BACI under Etalab Open Licence 2.0 — attribution required.
