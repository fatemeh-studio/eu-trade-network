"""Targeted-vs-random node removal and network fragmentation."""

from __future__ import annotations

from collections.abc import Hashable, Sequence

import networkx as nx
import numpy as np
import pandas as pd

from . import config

#: Strategy labels used in the tidy output of :func:`run_random_vs_targeted`.
RANDOM_STRATEGY: str = "random"
STRENGTH_STRATEGY: str = "targeted (out-strength)"
BETWEENNESS_STRATEGY: str = "targeted (betweenness)"

_CURVE_COLUMNS: list[str] = [
    "n_removed",
    "removed_node",
    "fraction_removed",
    "lcc_size",
    "lcc_fraction",
    "trade_value_retained",
]


def largest_weak_component_fraction(graph: nx.DiGraph) -> float:
    """Fraction of nodes in the largest weakly-connected component.

    Normalised by the graph's *current* node count, so a network that is still in one
    piece scores 1.0 however many nodes have already been removed. Fragmentation then
    shows up as a genuine drop rather than as the trivial shrinkage of the node set.

    Args:
        graph: Directed graph (possibly already thinned by node removal).

    Returns:
        ``|largest weakly-connected component| / |nodes|``, or 0.0 for an empty graph.
    """
    n_nodes = graph.number_of_nodes()
    if n_nodes == 0:
        return 0.0
    return len(_largest_weak_component(graph)) / n_nodes


def _largest_weak_component(graph: nx.DiGraph) -> set[Hashable]:
    """Node set of the largest weakly-connected component (ties broken deterministically)."""
    if graph.number_of_nodes() == 0:
        return set()
    return max(nx.weakly_connected_components(graph), key=lambda c: (len(c), min(c)))


def _weighted_betweenness(graph: nx.DiGraph) -> dict[Hashable, float]:
    """Betweenness using ``distance = 1 / value`` (trade value is a capacity, not a cost)."""
    distance_graph = graph.copy()
    for _u, _v, data in distance_graph.edges(data=True):
        value = float(data.get("weight", 1.0))
        data["distance"] = 1.0 / value if value > 0.0 else float("inf")
    return {
        node: float(score)
        for node, score in nx.betweenness_centrality(distance_graph, weight="distance").items()
    }


def _removal_order(graph: nx.DiGraph, order: str | Sequence[str], seed: int) -> list[Hashable]:
    """Resolve an order name (or an explicit sequence) into a concrete removal sequence."""
    nodes: list[Hashable] = list(graph.nodes)
    if not isinstance(order, str):
        sequence: list[Hashable] = list(order)
        unknown = [n for n in sequence if n not in graph]
        if unknown:
            raise ValueError(f"removal order contains nodes absent from the graph: {unknown}")
        if len(set(sequence)) != len(sequence):
            raise ValueError("removal order contains duplicate nodes")
        return sequence

    if order == "random":
        shuffled = sorted(nodes, key=str)
        np.random.default_rng(seed).shuffle(shuffled)  # type: ignore[arg-type]  # list is a MutableSequence
        return shuffled

    if order == "strength":
        ranking = {node: float(graph.out_degree(node, weight="weight")) for node in graph.nodes}
    elif order == "betweenness":
        ranking = _weighted_betweenness(graph)
    else:
        raise ValueError(
            f"unknown order {order!r}; expected 'random', 'strength', 'betweenness', "
            "or an explicit node sequence"
        )
    # Most central first; ISO3 breaks ties so the sequence is reproducible.
    return sorted(nodes, key=lambda node: (-ranking[node], str(node)))


def _snapshot(
    graph: nx.DiGraph, n_removed: int, n_nodes: int, total_value: float
) -> dict[str, object]:
    """Fragmentation metrics for the surviving sub-network after ``n_removed`` removals."""
    component = _largest_weak_component(graph)
    retained = sum(
        float(w)
        for u, v, w in graph.edges(data="weight", default=1.0)
        if u in component and v in component
    )
    n_surviving = graph.number_of_nodes()
    return {
        "n_removed": int(n_removed),
        "fraction_removed": n_removed / n_nodes,
        "lcc_size": len(component),
        "lcc_fraction": len(component) / n_surviving if n_surviving else 0.0,
        "trade_value_retained": retained / total_value if total_value > 0.0 else 0.0,
    }


def simulate_removal(
    graph: nx.DiGraph, order: str | Sequence[str], seed: int = config.RANDOM_SEED
) -> pd.DataFrame:
    """Remove nodes one at a time and track fragmentation.

    Targeted rankings are computed **once** on the intact graph (a static attack), so the
    sequence is a property of the observed network rather than of the removal path. Trade
    value is credited only to edges with *both* endpoints inside the largest weakly-connected
    component: value stranded in a splinter component counts as lost.

    Args:
        graph: Directed weighted trade graph (edge ``weight`` = value_kusd).
        order: ``"random"``, ``"strength"``, ``"betweenness"``, or an explicit node order.
        seed: Seed for the ``"random"`` order (ignored otherwise).

    Returns:
        DataFrame with columns ``fraction_removed``, ``lcc_fraction``,
        ``trade_value_retained`` (share of total edge value still inside the LCC),
        plus ``n_removed``, ``removed_node`` and ``lcc_size``. The first row is the
        intact network (nothing removed).
    """
    n_nodes = graph.number_of_nodes()
    if n_nodes == 0:
        return pd.DataFrame(columns=_CURVE_COLUMNS)

    total_value = float(sum(float(w) for _u, _v, w in graph.edges(data="weight", default=1.0)))
    sequence = _removal_order(graph, order, seed)

    working: nx.DiGraph = graph.copy()
    first = _snapshot(working, 0, n_nodes, total_value)
    first["removed_node"] = None
    rows: list[dict[str, object]] = [first]
    for step, node in enumerate(sequence, start=1):
        working.remove_node(node)
        row = _snapshot(working, step, n_nodes, total_value)
        row["removed_node"] = node
        rows.append(row)

    return pd.DataFrame(rows).reindex(columns=_CURVE_COLUMNS)


def run_random_vs_targeted(graph: nx.DiGraph, n_random_runs: int = 20) -> pd.DataFrame:
    """Random removal (averaged over seeded runs) vs targeted removal — tidy long form.

    Random failure is averaged over ``n_random_runs`` runs seeded from
    ``config.RANDOM_SEED`` (seed ``RANDOM_SEED + run``); the standard deviation across
    runs is reported alongside. Targeted attacks are deterministic, so their spread is 0.

    Args:
        graph: Directed weighted trade graph.
        n_random_runs: Number of seeded random-removal runs to average.

    Returns:
        Long-form DataFrame with one row per (``strategy``, removal step) and columns
        ``strategy``, ``n_removed``, ``fraction_removed``, ``lcc_fraction``,
        ``lcc_fraction_sd``, ``trade_value_retained``, ``trade_value_retained_sd``.
    """
    if n_random_runs < 1:
        raise ValueError("n_random_runs must be at least 1")

    columns = [
        "strategy",
        "n_removed",
        "fraction_removed",
        "lcc_fraction",
        "lcc_fraction_sd",
        "trade_value_retained",
        "trade_value_retained_sd",
    ]
    if graph.number_of_nodes() == 0:
        return pd.DataFrame(columns=columns)

    runs = pd.concat(
        [
            simulate_removal(graph, "random", seed=config.RANDOM_SEED + run)
            for run in range(n_random_runs)
        ],
        ignore_index=True,
    )
    random_curve = pd.DataFrame(
        runs.groupby("n_removed", as_index=False).agg(
            fraction_removed=("fraction_removed", "first"),
            lcc_fraction=("lcc_fraction", "mean"),
            lcc_fraction_sd=("lcc_fraction", "std"),
            trade_value_retained=("trade_value_retained", "mean"),
            trade_value_retained_sd=("trade_value_retained", "std"),
        )
    )
    # A single run has no spread; report 0 rather than NaN so the band code stays uniform.
    for sd_col in ("lcc_fraction_sd", "trade_value_retained_sd"):
        random_curve[sd_col] = random_curve[sd_col].astype(float).fillna(0.0)
    random_curve["strategy"] = RANDOM_STRATEGY

    frames: list[pd.DataFrame] = [random_curve]
    for strategy, order in ((STRENGTH_STRATEGY, "strength"), (BETWEENNESS_STRATEGY, "betweenness")):
        curve = simulate_removal(graph, order).drop(columns=["removed_node", "lcc_size"])
        curve["strategy"] = strategy
        curve["lcc_fraction_sd"] = 0.0
        curve["trade_value_retained_sd"] = 0.0
        frames.append(curve)

    return pd.concat(frames, ignore_index=True).reindex(columns=columns)


def _first_crossing(curve: pd.DataFrame, column: str, level: float) -> float:
    """First ``fraction_removed`` at which ``column`` falls below ``level`` (else ``nan``)."""
    missing = {"fraction_removed", column} - set(curve.columns)
    if missing:
        raise ValueError(f"curve missing columns: {sorted(missing)}")
    if "strategy" in curve.columns and len(set(curve["strategy"])) > 1:
        raise ValueError("pass a single-strategy curve (filter on 'strategy' first)")

    ordered = curve.sort_values("fraction_removed")
    below = ordered.loc[ordered[column].astype(float) < level]
    if below.empty:
        return float("nan")
    return float(below["fraction_removed"].to_numpy(dtype=float)[0])


def critical_threshold(curve: pd.DataFrame, lcc_level: float = 0.5) -> float:
    """Fraction of nodes removed at which the LCC first drops below ``lcc_level``.

    A dense, near-complete trade graph only ever fragments once it is emptied, in which
    case the returned threshold is 1.0 — read that as "does not fragment".

    Args:
        curve: Removal curve for a **single** strategy, with columns ``fraction_removed``
            and ``lcc_fraction`` (e.g. one strategy slice of
            :func:`run_random_vs_targeted`).
        lcc_level: Share of surviving nodes the largest component must fall below.

    Returns:
        The first ``fraction_removed`` whose ``lcc_fraction`` is below ``lcc_level``,
        or ``nan`` if the curve never gets there.
    """
    return _first_crossing(curve, "lcc_fraction", lcc_level)


def value_threshold(curve: pd.DataFrame, value_level: float = 0.5) -> float:
    """Fraction of nodes removed at which retained trade value first drops below ``value_level``.

    The economic counterpart of :func:`critical_threshold`: a dense network can stay in
    one piece while most of the value it carries has already gone.

    Args:
        curve: Removal curve for a **single** strategy, with columns ``fraction_removed``
            and ``trade_value_retained``.
        value_level: Share of the original trade value to fall below.

    Returns:
        The first ``fraction_removed`` whose ``trade_value_retained`` is below
        ``value_level``, or ``nan`` if the curve never gets there.
    """
    return _first_crossing(curve, "trade_value_retained", value_level)
