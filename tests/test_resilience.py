"""Unit tests for node-removal resilience on graphs with a known fragmentation point."""

from __future__ import annotations

import math

import networkx as nx
import pytest

from eu_trade_network.resilience import (
    BETWEENNESS_STRATEGY,
    RANDOM_STRATEGY,
    STRENGTH_STRATEGY,
    critical_threshold,
    largest_weak_component_fraction,
    run_random_vs_targeted,
    simulate_removal,
    value_threshold,
)


@pytest.fixture
def star_digraph() -> nx.DiGraph:
    """Hub H plus five spokes, reciprocal edges — losing H shatters the network."""
    g = nx.DiGraph()
    for spoke in "ABCDE":
        g.add_edge("H", spoke, weight=10.0)
        g.add_edge(spoke, "H", weight=10.0)
    return g


@pytest.fixture
def path_digraph() -> nx.DiGraph:
    """Reciprocal path A–B–C–D–E: removing the middle node C splits it in two halves."""
    g = nx.DiGraph()
    for u, v in zip("ABCD", "BCDE", strict=True):
        g.add_edge(u, v, weight=1.0)
        g.add_edge(v, u, weight=1.0)
    return g


def test_largest_weak_component_fraction(star_digraph: nx.DiGraph) -> None:
    assert largest_weak_component_fraction(star_digraph) == pytest.approx(1.0)

    shattered = star_digraph.copy()
    shattered.remove_node("H")
    # Five isolated spokes: the largest component holds one of the five survivors.
    assert largest_weak_component_fraction(shattered) == pytest.approx(0.2)
    assert largest_weak_component_fraction(nx.DiGraph()) == 0.0


def test_star_fragments_after_the_hub(star_digraph: nx.DiGraph) -> None:
    curve = simulate_removal(star_digraph, "strength")

    # Row 0 is the intact network; the hub carries all the strength, so it goes first.
    assert curve.loc[0, "lcc_fraction"] == pytest.approx(1.0)
    assert curve.loc[0, "trade_value_retained"] == pytest.approx(1.0)
    assert curve.loc[1, "removed_node"] == "H"
    assert curve.loc[1, "fraction_removed"] == pytest.approx(1 / 6)
    assert curve.loc[1, "lcc_fraction"] == pytest.approx(0.2)
    # Every edge touched the hub, so no trade value survives its removal.
    assert curve.loc[1, "trade_value_retained"] == pytest.approx(0.0)
    assert critical_threshold(curve) == pytest.approx(1 / 6)


def test_path_fragments_at_the_middle_node(path_digraph: nx.DiGraph) -> None:
    curve = simulate_removal(path_digraph, ["C"])

    assert len(curve) == 2
    # {A,B} and {D,E} — the largest component holds half the four survivors.
    assert curve.loc[1, "lcc_fraction"] == pytest.approx(0.5)
    # Of the four undirected links (8 directed edges), only A–B remains inside the LCC.
    assert curve.loc[1, "trade_value_retained"] == pytest.approx(0.25)
    assert critical_threshold(curve, lcc_level=0.6) == pytest.approx(0.2)


def test_random_removal_is_seeded_and_reproducible(star_digraph: nx.DiGraph) -> None:
    first = simulate_removal(star_digraph, "random", seed=7)
    again = simulate_removal(star_digraph, "random", seed=7)
    other = simulate_removal(star_digraph, "random", seed=8)

    assert first["removed_node"].tolist() == again["removed_node"].tolist()
    assert first["removed_node"].tolist() != other["removed_node"].tolist()


def test_targeted_beats_random_on_the_star(star_digraph: nx.DiGraph) -> None:
    curves = run_random_vs_targeted(star_digraph, n_random_runs=10)

    assert set(curves["strategy"]) == {RANDOM_STRATEGY, STRENGTH_STRATEGY, BETWEENNESS_STRATEGY}
    # Six nodes ⇒ seven steps (intact + one per removal) for each of the three strategies.
    assert len(curves) == 3 * 7

    by_strategy = {
        name: critical_threshold(frame) for name, frame in curves.groupby("strategy", sort=False)
    }
    assert by_strategy[STRENGTH_STRATEGY] == pytest.approx(1 / 6)
    assert by_strategy[BETWEENNESS_STRATEGY] == pytest.approx(1 / 6)
    # Random failure usually spares the hub for a while, so it fragments later on average.
    assert by_strategy[RANDOM_STRATEGY] > by_strategy[STRENGTH_STRATEGY]

    random_curve = curves.loc[curves["strategy"] == RANDOM_STRATEGY]
    assert float(random_curve["lcc_fraction_sd"].max()) > 0.0
    targeted = curves.loc[curves["strategy"] == STRENGTH_STRATEGY]
    assert float(targeted["lcc_fraction_sd"].max()) == 0.0


def test_complete_graph_never_fragments() -> None:
    complete = nx.DiGraph()
    for u in "ABCD":
        for v in "ABCD":
            if u != v:
                complete.add_edge(u, v, weight=1.0)

    curve = simulate_removal(complete, "strength")
    # Any subgraph of a complete digraph is still connected until nothing is left.
    assert curve["lcc_fraction"].tolist()[:-1] == [1.0] * 4
    # Value decays as edges are lost even though connectivity never breaks.
    assert curve["trade_value_retained"].tolist() == pytest.approx([1.0, 0.5, 1 / 6, 0.0, 0.0])
    assert critical_threshold(curve) == pytest.approx(1.0)
    assert value_threshold(curve) == pytest.approx(0.5)


def test_critical_threshold_validates_input(star_digraph: nx.DiGraph) -> None:
    curves = run_random_vs_targeted(star_digraph, n_random_runs=2)
    with pytest.raises(ValueError, match="single-strategy"):
        critical_threshold(curves)

    intact_only = simulate_removal(star_digraph, []).drop(columns=["lcc_fraction"])
    with pytest.raises(ValueError, match="missing columns"):
        critical_threshold(intact_only)

    never = simulate_removal(star_digraph, [])
    assert math.isnan(critical_threshold(never))


def test_unknown_order_raises(star_digraph: nx.DiGraph) -> None:
    with pytest.raises(ValueError, match="unknown order"):
        simulate_removal(star_digraph, "popularity")
    with pytest.raises(ValueError, match="absent from the graph"):
        simulate_removal(star_digraph, ["Z"])
    with pytest.raises(ValueError, match="duplicate"):
        simulate_removal(star_digraph, ["A", "A"])
