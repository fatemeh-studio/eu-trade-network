# PROGRESS

Living status file. Update after every prompt (see `docs/CURSOR_PROMPTS.md`).
Status: ⬜ todo · 🟡 in progress · ✅ done

## Build sequence
- ✅ **P0** Bootstrap — conda env, `pip install -e .`, pre-commit, tooling green
- ✅ **P1** `config.py` + `data_loader.py` (load BACI, map ISO3, filter, aggregate)
- ✅ **P2** `graph.py` + `db.py` + `schema.sql` → **NB01** graph + hero flow map
- ✅ **P3** `metrics.py` (centrality, backbone, rich-club) → **NB02** rankings (Austria)
- ⬜ **P4** `communities.py` → **NB03** Louvain blocs + geo map + PyVis
- ⬜ **P5** `resilience.py` → **NB04** targeted vs random + critical threshold
- ⬜ **P6** *(optional)* **NB05** energy (HS-27) subnetwork — bridge to energy project
- ⬜ **P7** `index.qmd` report + README findings + headline figures + `v0.1.0` tag

## Key findings (fill as you go)
- RQ1 centrality / Austria rank: Germany dominates weighted betweenness (0.829);
  only 15/35 economies have positive betweenness on this complete digraph
  (density = 1). Austria is among the 20 with betweenness = 0 (not a bridge —
  partners already trade directly). Mid-tier by volume: 17th of 35 by export
  strength, 13th by PageRank; top partner Germany both ways. Disparity filter
  keeps 184/1190 edges at α = 0.05 (`figures/headline/02_backbone_map.png`).
- RQ2 communities (K, modularity): …
- RQ3 resilience (critical fraction): …
- RQ4 energy subnetwork: …

## Decisions log
- Data source: CEPII BACI (chosen over UN Comtrade API — no key/rate-limit friction;
  academic-standard reconciled data). Year: see `config.YEAR`.
- Dense weighted network → disparity-filter backbone instead of scale-free/small-world
  framing (that framing belongs to the sibling air-transport project).

## Current next step
> Run **P4** from `docs/CURSOR_PROMPTS.md`.
