# PROGRESS

Living status file. Update after every prompt (see `docs/CURSOR_PROMPTS.md`).
Status: ⬜ todo · 🟡 in progress · ✅ done

## Build sequence
- ✅ **P0** Bootstrap — conda env, `pip install -e .`, pre-commit, tooling green
- ✅ **P1** `config.py` + `data_loader.py` (load BACI, map ISO3, filter, aggregate)
- ✅ **P2** `graph.py` + `db.py` + `schema.sql` → **NB01** graph + hero flow map
- ✅ **P3** `metrics.py` (centrality, backbone, rich-club) → **NB02** rankings (Austria)
- ✅ **P4** `communities.py` → **NB03** Louvain blocs + geo map + PyVis
- ✅ **P5** `resilience.py` → **NB04** targeted vs random + critical threshold
- ✅ **P6** `energy.py` → **NB05** energy (HS-27) subnetwork — bridge to energy project
- ⬜ **P7** `index.qmd` report + README findings + headline figures + `v0.1.0` tag

## Key findings (fill as you go)
- RQ1 centrality / Austria rank: Germany dominates weighted betweenness (0.829);
  only 15/35 economies have positive betweenness on this complete digraph
  (density = 1). Austria is among the 20 with betweenness = 0 (not a bridge —
  partners already trade directly). Mid-tier by volume: 17th of 35 by export
  strength, 13th by PageRank; top partner Germany both ways. Disparity filter
  keeps 184/1190 edges at α = 0.05 (`figures/headline/02_backbone_map.png`).
- RQ2 communities (K, modularity): Weighted Louvain finds **K = 3** blocs. The
  disparity-filter backbone gives the clearer partition (**Q = 0.25** vs 0.15 on the
  full dense graph). Blocs are **geographic, not political**: (1) a German-anchored
  continental core (23 economies, 22 EU-27 + CHE), (2) a Nordic-Baltic cluster
  (NOR, SWE, DNK, FIN, EST), (3) an extra-European partner bloc (USA, CHN, JPN, RUS,
  GBR, TUR + IRL). The EU-27 splits across all three; non-members CHE/NOR sit inside
  EU clusters while EU-member Ireland defects to the US-led bloc
  (`figures/headline/03_community_map.png`, `network_viz/03_trade_communities.html`).
- RQ3 resilience (critical fraction): Connectivity is **not** the weak point — the full
  graph is complete (density = 1), so it never fragments; the informative object is the
  disparity-filter backbone. There the **critical fraction is 34%** (12 of 35 economies)
  under betweenness-targeted removal and **40%** (14) under export-strength targeting,
  versus **89%** (31) under random failure — ≈2.6× more tolerant of accidents than of a
  targeted hit list; bridge economies bite ~2 economies sooner than big exporters. Value
  is far more fragile than topology: losing **3 economies (CHN, DEU, USA — 9% of nodes)
  halves total trade value**, while random failure needs 10 (29%). Germany alone carries
  27% of network value, China 25%, Austria 4.0% (17th by export volume, not a chokepoint)
  (`figures/headline/04_resilience.png`, `figures/qa/04_resilience_full_graph.png`).
- RQ4 energy subnetwork: HS-27 is **12% of the network's value** but a far more
  concentrated market: the **top 3 exporters carry 55%** of energy exports
  (RUS 23%, NOR 18%, USA 13%) against **38%** for merchandise (CHN, DEU, USA) —
  HHI **0.124 vs 0.075**, i.e. **8 effective suppliers instead of 13**. Density stays
  high (0.96), so again it is concentration, not connectivity, that carries the risk.
  Austria is **12th of 35 by energy exports** (0.9%) and **18th by imports**, a net
  importer (−5.5 bn USD); its energy exports are re-exports and transit (53%
  electricity, 26% gas), and 59% of its energy imports arrive via Germany. Two caveats
  that matter: only **48% of the node set's energy imports originate inside it**
  (65% for merchandise), so the real suppliers (Gulf, Kazakhstan, Africa) are outside
  the frame; and **pipeline gas is misattributed** in customs data — BACI shows Austria
  as a net gas exporter in 2022, which it was not. Bridge: **electricity (HS-2716)** is
  9% of the energy network but 53% of Austria's energy exports (5.9 bn out vs 5.7 bn in,
  with DEU/CHE/HUN/SVN) — the same flow `austria-energy-analysis` measures hourly
  (`figures/headline/05_energy_subnetwork.png`).

## Decisions log
- Data source: CEPII BACI (chosen over UN Comtrade API — no key/rate-limit friction;
  academic-standard reconciled data). Year: see `config.YEAR`.
- Dense weighted network → disparity-filter backbone instead of scale-free/small-world
  framing (that framing belongs to the sibling air-transport project).
- RQ4 keeps the same 35-economy node set as RQ1–RQ3 for comparability, and reports the
  resulting blind spot explicitly (`energy.import_sourcing`) instead of widening it.

## Current next step
> Run **P7** (report, README findings, `v0.1.0` tag) from `docs/CURSOR_PROMPTS.md`.
