"""Trade-bloc detection via Louvain on an undirected weighted projection."""

from __future__ import annotations

import networkx as nx
import pandas as pd

from . import config


def to_undirected_weighted(graph: nx.DiGraph) -> nx.Graph:
    """Collapse i→j and j→i into one undirected edge whose weight is their sum.

    Node attributes are preserved. Self-loops are dropped (a country is not its own
    trade partner). The resulting simple graph is what Louvain runs on.

    Args:
        graph: Directed weighted trade graph (edge ``weight`` = value_kusd).

    Returns:
        Undirected weighted graph where edge ``weight`` = value(i→j) + value(j→i).
    """
    undirected = nx.Graph()
    undirected.add_nodes_from(graph.nodes(data=True))
    for u, v, data in graph.edges(data=True):
        if u == v:
            continue
        w = float(data.get("weight", 0.0))
        if undirected.has_edge(u, v):
            undirected[u][v]["weight"] += w
        else:
            undirected.add_edge(u, v, weight=w)
    return undirected


def _partition_to_sets(partition: dict[str, int]) -> list[set[str]]:
    """Group an ISO3 → community-id mapping into a list of node sets."""
    buckets: dict[int, set[str]] = {}
    for node, comm in partition.items():
        buckets.setdefault(int(comm), set()).add(str(node))
    return [buckets[c] for c in sorted(buckets)]


def detect_communities(
    undirected: nx.Graph, resolution: float = 1.0, seed: int = config.RANDOM_SEED
) -> dict[str, int]:
    """Louvain partition → mapping ISO3 → community id (weighted).

    Uses NetworkX's weighted Louvain (:func:`networkx.community.louvain_communities`)
    seeded from ``config.RANDOM_SEED`` for reproducibility. Community ids are assigned
    deterministically: largest community first (ties broken by smallest member ISO3),
    so the same partition always yields the same integer labels.

    Args:
        undirected: Undirected weighted graph (edge ``weight`` = summed trade value).
        resolution: Louvain resolution; >1 favours more, smaller communities.
        seed: Random seed for the Louvain optimisation.

    Returns:
        Mapping of ISO3 code → community id (0-based, contiguous).
    """
    communities = nx.community.louvain_communities(
        undirected, weight="weight", resolution=resolution, seed=seed
    )
    ordered = sorted(communities, key=lambda members: (-len(members), min(members)))
    partition: dict[str, int] = {}
    for comm_id, members in enumerate(ordered):
        for node in members:
            partition[str(node)] = comm_id
    return partition


def modularity(undirected: nx.Graph, partition: dict[str, int]) -> float:
    """Weighted modularity of a partition (higher = stronger community structure).

    Args:
        undirected: Undirected weighted graph the partition was computed on.
        partition: Mapping ISO3 → community id.

    Returns:
        Newman–Girvan modularity ``Q`` using edge ``weight``.
    """
    if undirected.number_of_edges() == 0:
        return 0.0
    return float(
        nx.community.modularity(undirected, _partition_to_sets(partition), weight="weight")
    )


def community_summary(
    partition: dict[str, int],
    node_meta: pd.DataFrame,
    undirected: nx.Graph | None = None,
) -> pd.DataFrame:
    """Per-community size, members, and total exports; plus overall modularity.

    One row per community with its member count, member ISO3 list (largest exporter
    first), and total export strength. When ``undirected`` is supplied, the overall
    weighted modularity is stored in ``result.attrs["modularity"]``.

    Args:
        partition: Mapping ISO3 → community id.
        node_meta: Node table with at least ``iso3``; ``out_strength`` and ``name``
            are used when present.
        undirected: Optional graph the partition came from, to compute modularity.

    Returns:
        DataFrame with columns ``community``, ``n_countries``, ``members``,
        ``total_exports_kusd`` (sorted by exports, largest first).
    """
    comm_lookup = {str(k): int(v) for k, v in partition.items()}
    meta = node_meta.copy()
    meta["iso3"] = meta["iso3"].astype(str)
    meta = meta[meta["iso3"].isin(comm_lookup)].copy()
    meta["community"] = [comm_lookup[i] for i in meta["iso3"]]

    if "out_strength" in meta.columns:
        meta["out_strength"] = meta["out_strength"].astype(float)
    else:
        meta["out_strength"] = 0.0

    rows: list[dict[str, object]] = []
    for comm_id in sorted({int(c) for c in meta["community"]}):
        frame = meta.loc[meta["community"] == comm_id]
        ordered = frame.sort_values("out_strength", ascending=False)
        rows.append(
            {
                "community": int(comm_id),
                "n_countries": int(len(ordered)),
                "members": ", ".join(ordered["iso3"].tolist()),
                "total_exports_kusd": float(ordered["out_strength"].to_numpy(dtype=float).sum()),
            }
        )

    summary = (
        pd.DataFrame(rows).sort_values("total_exports_kusd", ascending=False).reset_index(drop=True)
    )
    if undirected is not None:
        summary.attrs["modularity"] = modularity(undirected, partition)
    return summary
