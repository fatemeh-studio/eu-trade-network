# European Trade Network

> Complex-systems analysis of European merchandise trade — **centrality**, **trade
> communities**, and **network resilience** — built from CEPII BACI open data.

![Trade flow map](figures/headline/01_flow_map.png)

## The question

Which economies hold the European trade network together, do coherent trade blocs
emerge from the flow structure, and how much of Europe's trade survives the loss of its
biggest hubs? This project models **countries as nodes** and **directed, weighted trade
flows as edges**, then applies network science to answer three questions — with Austria
as a running reference point.

## Research questions & key findings

<!-- Fill the [FILL] values from the notebooks. Keep the numbers specific. -->

**RQ1 — Who is central, and where does Austria rank?**
[FILL: e.g. "Germany dominates every centrality measure; Austria ranks Nth of 35 by
betweenness, higher than its raw trade volume would suggest, reflecting its bridging role
between Western and Central-Eastern Europe."]

**RQ2 — Do trade communities emerge, and do they follow geography?**
[FILL: e.g. "Louvain finds K communities (modularity = 0.XX). They broadly follow
geography but cut across EU membership — e.g. cluster X groups …"]

**RQ3 — How resilient is the network to hub failure?**
[FILL: e.g. "Removing the top N economies by strength fragments the network after X% of
nodes, versus Y% under random failure — the signature vulnerability of a hub-dominated
trade system."]

**RQ4 (optional) — Energy trade (HS-27) vs total trade**
[FILL: e.g. "The energy-commodity subnetwork is more concentrated: the top 3 exporters
account for Z% of energy flows vs W% of total flows."]

## Data

**CEPII BACI** — harmonised bilateral trade flows at HS-6 product level, 200+ countries.
Distributed under the Etalab Open Licence 2.0. Raw files are **not committed** (they are
large and versioned); see [`data/README.md`](data/README.md) for the one-time download
step. Scope: EU-27 plus major partners (~35 economies), year configurable in
`src/eu_trade_network/config.py`.

Source: Gaulier, G. & Zignago, S. (2010), *BACI: International Trade Database at the
Product-Level*, CEPII Working Paper N°2010-23.

## Methods

Directed weighted graph in NetworkX; DuckDB for storing node metrics, edges, and
community assignments and for the SQL rankings; **disparity-filter** backbone extraction
for a dense weighted network; **Louvain** community detection; targeted-vs-random
**resilience** simulation. Visuals in Plotly (geographic flow map), PyVis (interactive
network), and Matplotlib (distributions, resilience curves).

## Reproduce

```bash
# 1. Environment
conda env create -f environment.yml
conda activate eu-trade-network
pip install -e .
pre-commit install
# Notebook outputs are kept on disk but stripped from git via a local nbstripout
# filter. .gitattributes names the filter; each clone must configure it once:
nbstripout --install --attributes .gitattributes

# 2. Data — one-time manual download (see data/README.md)
#    place the BACI CSVs into data/raw/

# 3. Run the analysis notebooks in order
jupyter lab   # run notebooks/01 → 05 top-to-bottom

# 4. (optional) Render the report
quarto render
```

## Project structure

```
src/eu_trade_network/   analysis package (data, graph, metrics, communities, resilience, db, viz)
notebooks/              01 construction → 02 centrality+backbone → 03 communities → 04 resilience → 05 energy
sql/                    schema.sql + analytical queries
data/                   raw/ processed/ external/ (gitignored) · reference/ (committed)
figures/headline/       committed figures used in this README
```

## Related project

Sibling to [`austria-energy-analysis`](https://github.com/fatemeh-studio/austria-energy-analysis)
— RQ4 (energy-commodity subnetwork) is a deliberate bridge between the two.

## Licence

Code: MIT (see `LICENSE`). Data: CEPII BACI under Etalab Open Licence 2.0 — attribution required.
