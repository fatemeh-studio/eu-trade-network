"""Unit tests for centrality / disparity-filter metrics on a tiny weighted digraph."""

from __future__ import annotations

import networkx as nx
import pytest

from eu_trade_network.metrics import (
    compute_centralities,
    disparity_filter,
    node_strength,
    rich_club,
)


@pytest.fixture
def toy_digraph() -> nx.DiGraph:
    """Small weighted digraph with a known weak outgoing edge from a hub.

    Hub A sends almost all of its exports to B; the tiny A→C link must be dropped
    by the disparity filter at alpha=0.05 (from A's out-neighbourhood). Extra edges
    give C and D degree > 1 so the weak link is not rescued from the importer side.
    """
    g = nx.DiGraph()
    g.add_edge("A", "B", weight=90.0)
    g.add_edge("A", "C", weight=1.0)  # weak — expect dropped
    g.add_edge("A", "D", weight=9.0)
    g.add_edge("B", "C", weight=5.0)
    g.add_edge("B", "D", weight=5.0)
    g.add_edge("C", "D", weight=5.0)
    g.add_edge("D", "C", weight=5.0)
    return g


def test_node_strength_in_out(toy_digraph: nx.DiGraph) -> None:
    strength = node_strength(toy_digraph).set_index("iso3")
    assert strength.loc["A", "out_strength"] == pytest.approx(100.0)
    assert strength.loc["A", "in_strength"] == pytest.approx(0.0)
    assert strength.loc["B", "in_strength"] == pytest.approx(90.0)
    assert strength.loc["B", "out_strength"] == pytest.approx(10.0)
    assert strength.loc["C", "in_strength"] == pytest.approx(11.0)
    assert strength.loc["D", "in_strength"] == pytest.approx(19.0)


def test_disparity_filter_drops_weak_edge(toy_digraph: nx.DiGraph) -> None:
    backbone = disparity_filter(toy_digraph, alpha=0.05)
    assert backbone.has_edge("A", "B")
    assert not backbone.has_edge("A", "C")
    # All original nodes retained.
    assert set(backbone.nodes) == set(toy_digraph.nodes)


def test_compute_centralities_columns(toy_digraph: nx.DiGraph) -> None:
    cent = compute_centralities(toy_digraph)
    expected = {
        "iso3",
        "in_strength",
        "out_strength",
        "degree",
        "betweenness",
        "betweenness_u",
        "eigenvector",
        "pagerank",
    }
    assert expected.issubset(set(cent.columns))
    assert set(cent["iso3"]) == {"A", "B", "C", "D"}
    assert cent["pagerank"].sum() == pytest.approx(1.0, rel=1e-5)


def test_rich_club_returns_frame(toy_digraph: nx.DiGraph) -> None:
    rc = rich_club(toy_digraph)
    assert list(rc.columns) == ["degree_k", "rich_club_coefficient"]
    assert len(rc) >= 1
