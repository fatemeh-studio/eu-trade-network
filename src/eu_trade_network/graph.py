"""Build the directed weighted trade graph and summarise it."""

from __future__ import annotations

from pathlib import Path

import networkx as nx
import pandas as pd

from . import config
from .geo import COUNTRY_COORDS


def build_graph(edgelist: pd.DataFrame, groups_csv: Path = config.COUNTRY_GROUPS_CSV) -> nx.DiGraph:
    """Build a directed weighted graph from a bilateral edge list.

    Edge i→j carries ``value_kusd`` as attribute ``weight``. Node ``name``/``grp``
    attributes are read from ``groups_csv`` (defaults to the committed reference file).
    Latitude and longitude come from ``geo.COUNTRY_COORDS``.

    Args:
        edgelist: DataFrame with ``exporter_iso3``, ``importer_iso3``, ``value_kusd``.
        groups_csv: Country metadata CSV (``iso3``, ``name``, ``group``).

    Returns:
        Directed NetworkX graph with node attributes ``name``, ``grp``, ``lat``, ``lon``.
    """
    groups = pd.read_csv(groups_csv).set_index("iso3")
    graph = nx.DiGraph()

    nodes = set(edgelist["exporter_iso3"].astype(str)) | set(edgelist["importer_iso3"].astype(str))
    for iso3 in sorted(nodes):
        if iso3 not in groups.index:
            raise KeyError(f"ISO3 '{iso3}' missing from {groups_csv}")
        if iso3 not in COUNTRY_COORDS:
            raise KeyError(f"ISO3 '{iso3}' missing from geo.COUNTRY_COORDS")
        row = groups.loc[iso3]
        lat, lon = COUNTRY_COORDS[iso3]
        graph.add_node(
            iso3,
            name=str(row["name"]),
            grp=str(row["group"]),
            lat=float(lat),
            lon=float(lon),
        )

    for exporter, importer, value in edgelist[
        ["exporter_iso3", "importer_iso3", "value_kusd"]
    ].itertuples(index=False, name=None):
        graph.add_edge(str(exporter), str(importer), weight=float(value))

    return graph


def graph_summary(graph: nx.DiGraph) -> dict[str, float]:
    """Headline stats: n_nodes, n_edges, density, is_weakly_connected, total_value_kusd.

    Args:
        graph: Directed weighted trade graph.

    Returns:
        Dict of float stats (``is_weakly_connected`` is 1.0 or 0.0).
    """
    total_value = float(sum(data["weight"] for _, _, data in graph.edges(data=True)))
    return {
        "n_nodes": float(graph.number_of_nodes()),
        "n_edges": float(graph.number_of_edges()),
        "density": float(nx.density(graph)),
        "is_weakly_connected": float(nx.is_weakly_connected(graph)),
        "total_value_kusd": total_value,
    }
