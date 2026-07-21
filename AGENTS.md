# AGENTS.md — operating rules for the Cursor agent (Grok 4.5)

You are building **eu-trade-network**: a complex-systems analysis of the European
merchandise-trade network. Follow these rules on **every** action. Do not ask the
user questions unless a task is genuinely blocked — proceed and state assumptions.

## Environment
- OS: Ubuntu. Package manager: **conda**. Never `pip install` into the base env.
- The project env is `eu-trade-network` (see `environment.yml`).
- The package is installed editable: `pip install -e .` (inside the conda env).
- Config values (year, country sets, paths) live in `src/eu_trade_network/config.py`.
  Never hard-code paths or country lists in notebooks — import from `config`.

## Code style & quality (must pass before any task is "done")
- `ruff check .` → clean. `ruff format .` → applied.
- `basedpyright` → no errors (mode: standard). Add full **type hints** on every
  public function.
- **Google-style docstrings** on every public function/class.
- Prefer pure, testable functions. Reusable logic goes in the package, never in a
  notebook.
- Set random seeds from `config.RANDOM_SEED` anywhere randomness is used
  (resilience runs, layout, Louvain).

## Repository layout (respect it)
- `src/eu_trade_network/` — all analysis logic (data, graph, metrics, communities,
  resilience, db, viz). Notebooks **orchestrate and visualise only**.
- `notebooks/` — `01_…` → `05_…`, each runnable top-to-bottom after
  `Restart & Run All`.
- `sql/schema.sql` + `sql/queries/*.sql` — DuckDB schema and analytical queries.
- `figures/headline/` — committed PNGs used in the README. `figures/qa/` — gitignored.
- `data/` — everything under `raw/`, `processed/`, `external/` is **gitignored**.
  Only `data/reference/` is committed.

## Data rules
- Primary source is **CEPII BACI** (see `data/README.md`). The raw BACI CSVs are a
  **manual, one-time download** by the user into `data/raw/`. Do **not** attempt to
  scrape or auto-download them.
- If BACI files are missing, `data_loader.find_baci_files` must raise a
  `FileNotFoundError` whose message tells the user exactly what to download and where
  to put it. Never fail silently or fabricate data.
- Trade values (`v`) are in **thousands of USD**. Quantity (`q`) is metric tons and is
  missing in ~2% of rows — do not rely on it.

## Git
- Conventional commits: `feat:`, `fix:`, `docs:`, `chore:`, `refactor:`, `test:`.
- One logical change per commit. Never use "update" / "wip" as a message.
- After finishing each Prompt in `docs/CURSOR_PROMPTS.md`, make a single commit and
  update `PROGRESS.md`.
- `nbstripout` runs via pre-commit and strips notebook outputs — commit notebooks with
  code but no output. Never disable it.

## Verification checklist (run at the end of every prompt)
1. `ruff check . && ruff format --check .`
2. `basedpyright`
3. `pytest`
4. If a notebook changed: run `Restart & Run All`; confirm it completes with no errors.
5. If `index.qmd` changed: `quarto render` succeeds.
6. Commit + update `PROGRESS.md`.

## Analytical correctness (this project is judged on rigour — get these right)
- The graph is **directed and weighted**: an edge i→j carries `value_kusd` = exports
  from i to j. Node **out-strength** = total exports, **in-strength** = total imports.
- **Betweenness on a weighted graph needs a *distance*, not a capacity.** Trade value is
  a capacity (bigger = closer), so add `distance = 1 / value_kusd` and pass that as the
  `weight` for betweenness/shortest-path metrics. Also report **unweighted** betweenness
  for the pure-topology view, and say which is which.
- **Eigenvector / PageRank** use `value_kusd` directly as `weight` (bigger = stronger).
- **Community detection** runs on an **undirected, weighted** projection (sum the i→j and
  j→i values into one edge weight). Report the **modularity** score.
- The trade graph is **dense**, so scale-free / small-world framing does **not** apply.
  Instead extract the **statistically significant backbone** with the **disparity filter**
  (Serrano, Boguñá & Vespignani, PNAS 2009) before visualising and before community
  detection where noted.
- **Resilience**: track the fraction of nodes in the **largest weakly-connected component**
  *and* the fraction of **total trade value retained** as nodes are removed. Compare
  **targeted** removal (by out-strength, then by betweenness) against **random** removal
  averaged over `config.RANDOM_SEED`-seeded runs. Report the critical fraction where the
  network fragments.

## Grok 4.5 operating notes
- Read this file and the relevant Prompt before editing. Make **minimal diffs**; do not
  refactor unrelated code.
- Use the terminal to actually run ruff / basedpyright / pytest and read the output —
  don't assume it passes.
- Keep going until the prompt's acceptance criteria are met; then stop and summarise
  what changed in 3–5 bullet points.
