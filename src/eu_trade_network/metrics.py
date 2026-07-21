"""Centrality, backbone extraction, and hierarchy metrics for a dense weighted graph."""

import networkx as nx
import pandas as pd

from . import config


def node_strength(graph: nx.DiGraph) -> pd.DataFrame:
    """Per-node in-strength (imports) and out-strength (exports)."""
    raise NotImplementedError("TODO: implement in Cursor Prompt P3")


def compute_centralities(graph: nx.DiGraph) -> pd.DataFrame:
    """Centrality table per node.

    Include: degree; weighted betweenness (use ``distance = 1 / value`` as the weight);
    unweighted betweenness (pure topology); eigenvector and PageRank (weight = value).
    Document which betweenness is which. Returns one row per ISO3.
    """
    raise NotImplementedError("TODO: implement in Cursor Prompt P3")


def disparity_filter(graph: nx.DiGraph, alpha: float = config.DISPARITY_ALPHA) -> nx.DiGraph:
    """Extract the statistically significant backbone (Serrano et al., PNAS 2009).

    Keep edges whose normalised weight is significant at level ``alpha`` given the
    node's degree. Returns a subgraph with the same nodes and the surviving edges.
    """
    raise NotImplementedError("TODO: implement in Cursor Prompt P3")


def rich_club(graph: nx.DiGraph) -> pd.DataFrame:
    """Rich-club coefficient vs node degree — do large economies trade preferentially?"""
    raise NotImplementedError("TODO: implement in Cursor Prompt P3")
