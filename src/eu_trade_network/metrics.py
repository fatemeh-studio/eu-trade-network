"""Centrality, backbone extraction, and hierarchy metrics for a dense weighted graph."""

from __future__ import annotations

import networkx as nx
import pandas as pd

from . import config

# PageRank / eigenvector on a dense weighted digraph can need many iterations.
_MAX_ITER: int = 10_000
_TOL: float = 1e-9


def node_strength(graph: nx.DiGraph) -> pd.DataFrame:
    """Per-node in-strength (imports) and out-strength (exports).

    Args:
        graph: Directed graph with edge attribute ``weight`` = trade value.

    Returns:
        DataFrame with columns ``iso3``, ``in_strength``, ``out_strength``.
    """
    rows: list[dict[str, float | str]] = []
    for node in graph.nodes:
        rows.append(
            {
                "iso3": str(node),
                "in_strength": float(graph.in_degree(node, weight="weight")),
                "out_strength": float(graph.out_degree(node, weight="weight")),
            }
        )
    return pd.DataFrame(rows).sort_values("iso3").reset_index(drop=True)


def compute_centralities(graph: nx.DiGraph) -> pd.DataFrame:
    """Centrality table per node.

    Include: degree; weighted betweenness (use ``distance = 1 / value`` as the weight);
    unweighted betweenness (pure topology); eigenvector and PageRank (weight = value).
    Document which betweenness is which. Returns one row per ISO3.

    Columns:
        ``iso3``, ``degree``, ``in_strength``, ``out_strength``,
        ``betweenness`` (weighted, distance = 1/value),
        ``betweenness_u`` (unweighted topology),
        ``eigenvector``, ``pagerank``.

    Args:
        graph: Directed weighted trade graph (edge ``weight`` = value_kusd).

    Returns:
        One row per node with centrality measures.
    """
    strength = node_strength(graph)

    # Distance for shortest-path metrics: larger trade value ⇒ shorter distance.
    distance_graph = graph.copy()
    for _u, _v, data in distance_graph.edges(data=True):
        value = float(data["weight"])
        data["distance"] = 1.0 / value if value > 0.0 else float("inf")

    betweenness = nx.betweenness_centrality(distance_graph, weight="distance")
    betweenness_u = nx.betweenness_centrality(graph, weight=None)
    eigenvector = nx.eigenvector_centrality(graph, weight="weight", max_iter=_MAX_ITER, tol=_TOL)
    pagerank = nx.pagerank(graph, weight="weight", max_iter=_MAX_ITER, tol=_TOL)

    rows: list[dict[str, float | int | str]] = []
    for node in graph.nodes:
        iso3 = str(node)
        rows.append(
            {
                "iso3": iso3,
                "degree": int(graph.degree(node)),
                "betweenness": float(betweenness[node]),
                "betweenness_u": float(betweenness_u[node]),
                "eigenvector": float(eigenvector[node]),
                "pagerank": float(pagerank[node]),
            }
        )
    centralities = pd.DataFrame(rows)
    return (
        strength.merge(centralities, on="iso3", how="inner")
        .sort_values("iso3")
        .reset_index(drop=True)
    )


def _disparity_pvalue(weight: float, strength: float, degree: int) -> float:
    """Null-model p-value for one edge from a node's perspective (Serrano et al.).

    For degree 1 the null is degenerate; treat the sole edge as significant (p = 0).
    """
    if degree <= 1:
        return 0.0
    if strength <= 0.0 or weight <= 0.0:
        return 1.0
    p_ij = weight / strength
    # Numerical guard: p_ij can be 1.0 when a node has a single positive-weight edge
    # among zero-weight stubs, but degree>1 with p=1 ⇒ p-value 0.
    if p_ij >= 1.0:
        return 0.0
    return float((1.0 - p_ij) ** (degree - 1))


def disparity_filter(graph: nx.DiGraph, alpha: float = config.DISPARITY_ALPHA) -> nx.DiGraph:
    """Extract the statistically significant backbone (Serrano et al., PNAS 2009).

    Keep edges whose normalised weight is significant at level ``alpha`` given the
    node's degree. Returns a subgraph with the same nodes and the surviving edges.

    For a directed edge i→j, significance is tested from i's *out* neighbourhood and
    from j's *in* neighbourhood; the edge is kept if either side rejects the null
    (OR rule).

    Args:
        graph: Directed weighted graph (edge ``weight`` = value).
        alpha: Significance level (default ``config.DISPARITY_ALPHA``).

    Returns:
        Directed subgraph on the same node set with backbone edges only.
    """
    out_strength = {n: float(graph.out_degree(n, weight="weight")) for n in graph.nodes}
    in_strength = {n: float(graph.in_degree(n, weight="weight")) for n in graph.nodes}
    out_degree = {n: int(graph.out_degree(n)) for n in graph.nodes}
    in_degree = {n: int(graph.in_degree(n)) for n in graph.nodes}

    kept: list[tuple[str, str, dict[str, float]]] = []
    for u, v, data in graph.edges(data=True):
        w = float(data["weight"])
        p_out = _disparity_pvalue(w, out_strength[u], out_degree[u])
        p_in = _disparity_pvalue(w, in_strength[v], in_degree[v])
        if p_out < alpha or p_in < alpha:
            kept.append((str(u), str(v), {"weight": w}))

    backbone = nx.DiGraph()
    backbone.add_nodes_from(graph.nodes(data=True))
    backbone.add_edges_from(kept)
    return backbone


def rich_club(graph: nx.DiGraph) -> pd.DataFrame:
    """Rich-club coefficient vs node degree — do large economies trade preferentially?

    Computed on the undirected projection (reciprocated pairs become one edge) using
    NetworkX's unweighted rich-club coefficient φ(k).

    Args:
        graph: Directed trade graph.

    Returns:
        DataFrame with columns ``degree_k`` and ``rich_club_coefficient``.
    """
    undirected = graph.to_undirected()
    # NetworkX requires a simple graph without self-loops.
    undirected.remove_edges_from(nx.selfloop_edges(undirected))
    if undirected.number_of_edges() == 0:
        return pd.DataFrame(columns=["degree_k", "rich_club_coefficient"])

    phi = nx.rich_club_coefficient(undirected, normalized=False, seed=config.RANDOM_SEED)
    rows = [{"degree_k": int(k), "rich_club_coefficient": float(v)} for k, v in sorted(phi.items())]
    return pd.DataFrame(rows)
