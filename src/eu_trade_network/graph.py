"""Build the directed weighted trade graph and summarise it."""

from pathlib import Path

import networkx as nx
import pandas as pd

from . import config


def build_graph(edgelist: pd.DataFrame, groups_csv: Path = config.COUNTRY_GROUPS_CSV) -> nx.DiGraph:
    """Build a directed weighted graph from a bilateral edge list.

    Edge i→j carries ``value_kusd`` as attribute ``weight``. Node ``name``/``grp``
    attributes are read from ``groups_csv`` (defaults to the committed reference file).
    """
    raise NotImplementedError("TODO: implement in Cursor Prompt P2")


def graph_summary(graph: nx.DiGraph) -> dict[str, float]:
    """Headline stats: n_nodes, n_edges, density, is_weakly_connected, total_value_kusd."""
    raise NotImplementedError("TODO: implement in Cursor Prompt P2")
