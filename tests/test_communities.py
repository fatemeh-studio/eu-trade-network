"""Unit tests for Louvain community detection on a small, well-separated graph."""

from __future__ import annotations

import networkx as nx
import pandas as pd
import pytest

from eu_trade_network.communities import (
    community_summary,
    detect_communities,
    modularity,
    to_undirected_weighted,
)


@pytest.fixture
def two_clique_digraph() -> nx.DiGraph:
    """Two dense 3-node cliques joined by a single weak bridge → 2 clear communities."""
    g = nx.DiGraph()
    strong = [("A", "B"), ("B", "C"), ("A", "C"), ("D", "E"), ("E", "F"), ("D", "F")]
    for u, v in strong:
        g.add_edge(u, v, weight=100.0)
        g.add_edge(v, u, weight=100.0)
    # Weak inter-clique bridge (both directions).
    g.add_edge("C", "D", weight=1.0)
    g.add_edge("D", "C", weight=1.0)
    return g


def test_to_undirected_weighted_sums_both_directions(two_clique_digraph: nx.DiGraph) -> None:
    undirected = to_undirected_weighted(two_clique_digraph)
    assert not undirected.is_directed()
    assert undirected["A"]["B"]["weight"] == pytest.approx(200.0)
    assert undirected["C"]["D"]["weight"] == pytest.approx(2.0)
    assert undirected.number_of_nodes() == 6


def test_detect_two_communities_positive_modularity(two_clique_digraph: nx.DiGraph) -> None:
    undirected = to_undirected_weighted(two_clique_digraph)
    partition = detect_communities(undirected)

    assert set(partition) == set(undirected.nodes)
    assert len(set(partition.values())) == 2
    # Each clique lands in a single community.
    assert partition["A"] == partition["B"] == partition["C"]
    assert partition["D"] == partition["E"] == partition["F"]
    assert partition["A"] != partition["D"]

    assert modularity(undirected, partition) > 0.0


def test_detect_communities_is_deterministic(two_clique_digraph: nx.DiGraph) -> None:
    undirected = to_undirected_weighted(two_clique_digraph)
    assert detect_communities(undirected) == detect_communities(undirected)


def test_community_summary_reports_modularity(two_clique_digraph: nx.DiGraph) -> None:
    undirected = to_undirected_weighted(two_clique_digraph)
    partition = detect_communities(undirected)
    node_meta = pd.DataFrame(
        {
            "iso3": list("ABCDEF"),
            "out_strength": [300.0, 200.0, 201.0, 202.0, 200.0, 200.0],
        }
    )
    summary = community_summary(partition, node_meta, undirected=undirected)

    assert set(summary.columns) == {"community", "n_countries", "members", "total_exports_kusd"}
    assert int(summary["n_countries"].to_numpy().sum()) == 6
    assert summary.attrs["modularity"] > 0.0
