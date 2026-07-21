"""Targeted-vs-random node removal and network fragmentation."""

from collections.abc import Sequence

import networkx as nx
import pandas as pd

from . import config


def largest_weak_component_fraction(graph: nx.DiGraph) -> float:
    """Fraction of nodes in the largest weakly-connected component."""
    raise NotImplementedError("TODO: implement in Cursor Prompt P5")


def simulate_removal(
    graph: nx.DiGraph, order: str | Sequence[str], seed: int = config.RANDOM_SEED
) -> pd.DataFrame:
    """Remove nodes one at a time and track fragmentation.

    Args:
        order: ``"random"``, ``"strength"``, ``"betweenness"``, or an explicit node order.

    Returns:
        DataFrame with columns ``fraction_removed``, ``lcc_fraction``,
        ``trade_value_retained`` (share of total edge value still inside the LCC).
    """
    raise NotImplementedError("TODO: implement in Cursor Prompt P5")


def run_random_vs_targeted(graph: nx.DiGraph, n_random_runs: int = 20) -> pd.DataFrame:
    """Random removal (averaged over seeded runs) vs targeted removal — tidy long form."""
    raise NotImplementedError("TODO: implement in Cursor Prompt P5")


def critical_threshold(curve: pd.DataFrame, lcc_level: float = 0.5) -> float:
    """Fraction of nodes removed at which the LCC first drops below ``lcc_level``."""
    raise NotImplementedError("TODO: implement in Cursor Prompt P5")
