"""Trade-bloc detection via Louvain on an undirected weighted projection."""

import networkx as nx
import pandas as pd

from . import config


def to_undirected_weighted(graph: nx.DiGraph) -> nx.Graph:
    """Collapse i→j and j→i into one undirected edge whose weight is their sum."""
    raise NotImplementedError("TODO: implement in Cursor Prompt P4")


def detect_communities(
    undirected: nx.Graph, resolution: float = 1.0, seed: int = config.RANDOM_SEED
) -> dict[str, int]:
    """Louvain partition → mapping ISO3 → community id (weighted)."""
    raise NotImplementedError("TODO: implement in Cursor Prompt P4")


def community_summary(partition: dict[str, int], node_meta: pd.DataFrame) -> pd.DataFrame:
    """Per-community size, members, and total exports; plus overall modularity."""
    raise NotImplementedError("TODO: implement in Cursor Prompt P4")
