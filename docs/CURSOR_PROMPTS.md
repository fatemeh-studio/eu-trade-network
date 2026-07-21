# Cursor prompt sequence — eu-trade-network

Drive the whole build with these, in order, using the **Cursor Agent** on **Grok 4.5**.
Paste one prompt, let it finish and commit, then paste the next. Every prompt tells the
agent to follow `AGENTS.md` and to end with `ruff` + `basedpyright` + `pytest` green.

## Before you start (once)

```bash
# create the repo and push the scaffold
cd eu-trade-network
git init && git add -A && git commit -m "chore: project scaffold"
# GitHub (needs the gh CLI, or create the empty repo in the web UI first):
gh repo create fatemeh-studio/eu-trade-network --public --source . --remote origin --push
```

Then open the folder in Cursor and run **P0**.

> **One manual data step** (do it before P1's sanity check runs): follow
> `data/README.md` to download the CEPII BACI **HS17** zip and copy the year CSV +
> the two metadata CSVs into `data/raw/`. Everything else is scripted.

---

## P0 — Bootstrap
```
Read AGENTS.md. Get all tooling green.
1) Create the conda env from environment.yml and activate it.
2) pip install -e .
3) pre-commit install
4) Register a Jupyter kernel for this env (python -m ipykernel install --user --name eu-trade-network).
5) Run `ruff check .`, `ruff format --check .`, `basedpyright`, and `pytest`. Make them ALL pass. Fix config only — do not weaken any check.
Report python/ruff/basedpyright/pytest versions. Commit `chore: bootstrap env and tooling`. Set P0 to done in PROGRESS.md.
```

## P1 — Data loader
```
Read AGENTS.md and src/eu_trade_network/data_loader.py. Implement every function to load CEPII BACI from data/raw/ into a bilateral edge list, following the docstrings exactly.
- find_baci_files: glob data/raw for BACI_HS*_Y{year}_V*.csv, country_codes_V*.csv, product_codes_HS*_V*.csv; pick the newest version tag. If any file is missing, raise FileNotFoundError naming the missing pattern and pointing to data/README.md.
- load_country_codes: columns country_code(int), iso3, name (handle BACI's country_code/country_name/country_iso3 headers).
- load_baci: read with correct dtypes — i,j int; k str with leading zeros preserved; v,q float.
- attach_iso3; filter_countries (BOTH endpoints in config.COUNTRIES); filter_products (k startswith any prefix); build_edgelist = full pipeline aggregating value over products → [exporter_iso3, importer_iso3, value_kusd].
- Drop self-loops (exporter == importer).
Add tests/test_data_loader.py using a tiny SYNTHETIC DataFrame (must not require the real files): test the ISO3 mapping, country filter, product filter, and that duplicate product rows aggregate into one summed edge.
Acceptance: ruff + basedpyright + pytest pass. Commit `feat: BACI data loader and edge-list pipeline`. Update PROGRESS.md.
If the real BACI files are already in data/raw/, run a terminal sanity check printing n_nodes, n_edges, total value_kusd and paste the numbers; otherwise print the download reminder.
```

## P2 — Graph + DuckDB + NB01
```
Read AGENTS.md, graph.py, db.py, sql/schema.sql, viz.py.
1) Create src/eu_trade_network/geo.py with a dict of {iso3: (lat, lon)} for the 35 countries (capital or centroid coords).
2) Implement graph.build_graph (directed weighted DiGraph, weight=value_kusd, attach name/grp/lat/lon per node) and graph_summary.
3) Implement db.connect / init_schema / write_table / read_sql (DuckDB; create data/processed/ if missing).
4) Implement viz.plot_flow_map (Plotly scattergeo; nodes at lat/lon; top_n edges by value as lines) and viz.save_fig (PNG via kaleido to figures/headline or figures/qa).
5) Build notebooks/01_data_and_graph.ipynb: build the edge list for config.YEAR, build the graph, print graph_summary, write nodes+edges to trade.duckdb, draw the flow map, save figures/headline/01_flow_map.png.
Acceptance: NB01 runs top-to-bottom; all checks green; figure saved. Commit `feat: graph construction, DuckDB storage, flow map (NB01)`. Update PROGRESS.md and the README hero path.
```

## P3 — Centrality + backbone + NB02
```
Read AGENTS.md, metrics.py.
1) Implement node_strength; compute_centralities (degree; WEIGHTED betweenness using distance = 1/value; UNWEIGHTED betweenness; eigenvector; PageRank with weight=value — raise max_iter to converge); disparity_filter (Serrano, Boguná & Vespignani 2009 backbone at config.DISPARITY_ALPHA); rich_club.
2) Implement viz.plot_degree_distribution (strength distribution; note in the figure that the graph is dense — no power-law fit).
3) Build notebooks/02_centrality_and_backbone.ipynb: compute centralities, UPDATE the nodes table with them, run sql/queries/01_top_hubs_by_betweenness.sql and 03_austria_trade_partners.sql via db.read_sql and display; state in prose where Austria ranks and why; plot the strength distribution; extract + visualise the backbone; save one headline figure.
Add tests/test_metrics.py on a small known weighted digraph (assert in/out strengths; assert disparity_filter drops the expected weak edge).
Acceptance: all green; NB02 runs. Commit `feat: centrality, disparity-filter backbone, rich-club (NB02)`. Update PROGRESS.md and the RQ1 finding.
```

## P4 — Communities + NB03
```
Read AGENTS.md, communities.py.
1) Implement to_undirected_weighted (sum i→j and j→i into one weight); detect_communities (Louvain, weighted, seed=config.RANDOM_SEED — python-louvain or networkx.community.louvain_communities); community_summary (+ modularity).
2) Implement viz.plot_network_pyvis (node size=strength, colour=community → interactive HTML under network_viz/).
3) Build notebooks/03_communities.ipynb: detect communities on the undirected-weighted graph AND on the backbone, keep the clearer result; write community ids into the nodes table; run sql/queries/02_community_summary.sql; draw a geographic map coloured by community (Plotly) and export the PyVis HTML; discuss whether blocs follow EU membership / geography; report modularity.
Add tests/test_communities.py (two-clique graph → 2 communities, modularity > 0).
Acceptance: all green; NB03 runs; PyVis HTML produced. Commit `feat: Louvain communities and interactive network (NB03)`. Update PROGRESS.md and the RQ2 finding.
```

## P5 — Resilience + NB04
```
Read AGENTS.md, resilience.py.
1) Implement largest_weak_component_fraction; simulate_removal (orders: "random"/"strength"/"betweenness"/explicit order; track fraction_removed, lcc_fraction, trade_value_retained = share of total edge value still inside the LCC); run_random_vs_targeted (random averaged over n_random_runs seeded runs; tidy long form); critical_threshold.
2) Implement viz.plot_resilience (two panels: LCC fraction and trade value retained; targeted vs random).
3) Build notebooks/04_resilience.ipynb: run random vs targeted (by strength and by betweenness), plot curves, compute + report the critical fraction, write a plain-language infrastructure/policy interpretation; save the resilience curve as a headline figure.
Add tests/test_resilience.py (star or path graph with a known fragmentation point).
Acceptance: all green; NB04 runs. Commit `feat: resilience simulation and curves (NB04)`. Update PROGRESS.md and the RQ3 finding.
```

## P6 — Energy subnetwork + NB05  (optional)
```
Read AGENTS.md. Build notebooks/05_energy_subnetwork.ipynb — a bridge to austria-energy-analysis.
Build the edge list with products=config.HS_ENERGY (HS chapter 27); construct that subgraph; compare it to the total-trade network: top exporters, concentration (share of top 3 exporters), and Austria's position. Produce one comparison table and one figure. Add package code only if needed.
Acceptance: NB05 runs; all green. Commit `feat: energy (HS-27) subnetwork bridge (NB05)`. Update PROGRESS.md and the RQ4 finding.
If short on time, SKIP this prompt — it is optional.
```

## P7 — Report + README + release
```
Read AGENTS.md. Finalise for the portfolio.
1) Fill index.qmd from the notebook outputs (reference the headline figures; write the RQ sections + 3 takeaways). `quarto render` must succeed.
2) Replace every [FILL] in README.md with real numbers (ranks, modularity, critical fraction) and the correct hero image path.
3) Ensure figures/headline/ has one clean PNG per RQ; notebooks are output-stripped and run top-to-bottom.
4) Final green check: ruff, basedpyright, pytest, quarto render.
5) Commit `docs: report, README findings, headline figures`; then `git tag v0.1.0`.
(Optional) `quarto publish gh-pages` and add the live link to the README.
Update PROGRESS.md: mark all done; set 'Current next step' to 'Publish repo + write LinkedIn post'.
```

---

### If a prompt gets stuck
- Data errors → re-read `data/README.md`; check the three files are in `data/raw/` with matching version tags.
- PageRank/eigenvector non-convergence → increase `max_iter`, or run on the largest weakly-connected component.
- A check won't pass → tell the agent the exact ruff/basedpyright/pytest error and to fix the code (never to disable the check).
