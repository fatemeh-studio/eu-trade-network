"""Energy (HS-27) subnetwork: exporter concentration and country position vs total trade.

The energy subnetwork is the same node set as the full trade graph, restricted to the
products in ``config.HS_ENERGY``. Everything here compares that subgraph with the
all-merchandise graph, so the two always share a definition of "share" and "rank".
"""

from __future__ import annotations

import networkx as nx
import numpy as np
import pandas as pd

from . import config, data_loader, metrics

#: Short labels for the HS chapter-27 headings (4-digit level).
HS27_HEADINGS: dict[str, str] = {
    "2701": "Coal",
    "2702": "Lignite",
    "2703": "Peat",
    "2704": "Coke and semi-coke",
    "2705": "Coal gas",
    "2706": "Tar",
    "2707": "Coal-tar oils",
    "2708": "Pitch",
    "2709": "Crude oil",
    "2710": "Refined petroleum",
    "2711": "Petroleum gases (LNG and pipeline gas)",
    "2712": "Petroleum jelly and waxes",
    "2713": "Petroleum coke and bitumen",
    "2714": "Natural bitumen and asphalt",
    "2715": "Bituminous mixtures",
    "2716": "Electrical energy",
}

#: Accepted values for the ``direction`` argument of :func:`heading_composition`.
_DIRECTIONS: tuple[str, str, str] = ("total", "exports", "imports")


def trade_shares(graph: nx.DiGraph) -> pd.DataFrame:
    """Per-economy trade value, share of the network, and rank in both directions.

    Args:
        graph: Directed weighted trade graph (edge ``weight`` = value_kusd).

    Returns:
        One row per economy, sorted by export share (largest first), with columns
        ``iso3``, ``out_strength``, ``in_strength``, ``export_share``, ``import_share``,
        ``export_rank``, ``import_rank``, ``net_export_kusd``.

    Raises:
        ValueError: If the graph carries no trade value (shares would be undefined).
    """
    shares = metrics.node_strength(graph)
    total_exports = float(shares["out_strength"].to_numpy(dtype=float).sum())
    total_imports = float(shares["in_strength"].to_numpy(dtype=float).sum())
    if total_exports <= 0.0 or total_imports <= 0.0:
        raise ValueError("graph carries no trade value — shares are undefined")

    shares["export_share"] = shares["out_strength"] / total_exports
    shares["import_share"] = shares["in_strength"] / total_imports
    shares["export_rank"] = shares["export_share"].rank(ascending=False, method="min").astype(int)
    shares["import_rank"] = shares["import_share"].rank(ascending=False, method="min").astype(int)
    shares["net_export_kusd"] = shares["out_strength"] - shares["in_strength"]
    return shares.sort_values("export_share", ascending=False).reset_index(drop=True)


def concentration(shares: pd.DataFrame, top_k: int = 3) -> dict[str, float]:
    """How concentrated are exports on a handful of economies?

    Args:
        shares: Output of :func:`trade_shares`.
        top_k: Number of leading exporters in the headline share.

    Returns:
        Dict with ``top_k`` (as a float), ``top_k_share`` (combined share of the ``top_k``
        largest exporters), ``hhi`` (Herfindahl index of export shares) and
        ``effective_exporters`` (1 / HHI — the number of equal-sized exporters that would
        give the same concentration).

    Raises:
        ValueError: If ``shares`` did not come from :func:`trade_shares`.
    """
    if "export_share" not in shares.columns:
        raise ValueError("shares must come from trade_shares (missing 'export_share')")
    ranked = sorted((float(share) for share in shares["export_share"]), reverse=True)
    hhi = sum(share**2 for share in ranked)
    return {
        "top_k": float(top_k),
        "top_k_share": float(sum(ranked[:top_k])),
        "hhi": hhi,
        "effective_exporters": 1.0 / hhi if hhi > 0.0 else float("inf"),
    }


def country_position(shares: pd.DataFrame, iso3: str) -> dict[str, float]:
    """Rank, share, and net balance of one economy inside a network.

    Args:
        shares: Output of :func:`trade_shares`.
        iso3: ISO3 code of the economy to look up.

    Returns:
        Dict with ``export_rank``, ``import_rank``, ``export_share``, ``import_share``,
        ``net_export_kusd``, and ``n_economies``.

    Raises:
        KeyError: If ``iso3`` is not in the network.
    """
    row = shares.loc[shares["iso3"].astype(str) == iso3]
    if row.empty:
        raise KeyError(f"'{iso3}' is not in this network")
    record = row.iloc[0]
    return {
        "export_rank": float(record["export_rank"]),
        "import_rank": float(record["import_rank"]),
        "export_share": float(record["export_share"]),
        "import_share": float(record["import_share"]),
        "net_export_kusd": float(record["net_export_kusd"]),
        "n_economies": float(len(shares)),
    }


def _fmt_top_exporters(shares: pd.DataFrame, top_k: int) -> str:
    """Comma-separated ISO3 codes of the ``top_k`` largest exporters."""
    return ", ".join(shares["iso3"].astype(str).head(top_k))


def _fmt_position(position: dict[str, float], rank_key: str, share_key: str) -> str:
    """Render a rank + share pair as ``'12 of 35 (0.9%)'``."""
    return (
        f"{int(position[rank_key])} of {int(position['n_economies'])} ({position[share_key]:.1%})"
    )


def comparison_table(
    total: nx.DiGraph,
    energy: nx.DiGraph,
    focus_iso3: str = "AUT",
    top_k: int = 3,
    labels: tuple[str, str] = ("All merchandise", "Energy (HS-27)"),
) -> pd.DataFrame:
    """Side-by-side comparison of the full trade network and the energy subnetwork.

    A display table: every cell is a pre-formatted string, because the rows mix values,
    counts, shares, ranks, and country codes.

    Args:
        total: All-merchandise trade graph.
        energy: Energy-only subgraph on the same node set.
        focus_iso3: Economy whose position is reported (Austria by default).
        top_k: Number of leading exporters behind the concentration rows.
        labels: Column names for the two networks.

    Returns:
        DataFrame with columns ``metric`` plus the two ``labels``, one row per metric.
    """
    graphs: dict[str, nx.DiGraph] = dict(zip(labels, (total, energy), strict=True))
    shares = {label: trade_shares(graph) for label, graph in graphs.items()}
    conc = {label: concentration(shares[label], top_k=top_k) for label in labels}
    position = {label: country_position(shares[label], focus_iso3) for label in labels}
    value = {
        label: float(sum(d["weight"] for *_, d in graph.edges(data=True)))
        for label, graph in graphs.items()
    }
    reference_value = value[labels[0]]

    metrics_by_label: dict[str, dict[str, str]] = {}
    for label in labels:
        graph, share, position_, conc_ = graphs[label], shares[label], position[label], conc[label]
        metrics_by_label[label] = {
            "Trade value (bn USD)": f"{value[label] / 1e6:,.0f}",
            "Share of merchandise value": f"{value[label] / reference_value:.1%}",
            "Links present (density)": (f"{graph.number_of_edges():,} ({nx.density(graph):.2f})"),
            "Largest exporter": (f"{share['iso3'].iloc[0]} ({share['export_share'].iloc[0]:.1%})"),
            f"Top {top_k} exporters": _fmt_top_exporters(share, top_k),
            f"Top {top_k} export share": f"{conc_['top_k_share']:.1%}",
            "Herfindahl index (exports)": f"{conc_['hhi']:.3f}",
            "Effective no. of exporters (1/HHI)": f"{conc_['effective_exporters']:.1f}",
            f"{focus_iso3} export rank": _fmt_position(position_, "export_rank", "export_share"),
            f"{focus_iso3} import rank": _fmt_position(position_, "import_rank", "import_share"),
            f"{focus_iso3} net exports (bn USD)": f"{position_['net_export_kusd'] / 1e6:+,.1f}",
        }

    rows = [
        {"metric": metric, **{label: metrics_by_label[label][metric] for label in labels}}
        for metric in metrics_by_label[labels[0]]
    ]
    return pd.DataFrame(rows)


def import_sourcing(
    products: list[str] = config.HS_ENERGY,
    focus_iso3: str = "AUT",
    countries: list[str] = config.COUNTRIES,
    labels: tuple[str, str] = ("All merchandise", "Energy (HS-27)"),
) -> pd.DataFrame:
    """How much of the node set's imports is sourced *inside* the node set.

    The trade graph keeps only flows with both endpoints in ``countries``. That is the right
    object for network structure, but it hides imports from outside it — and energy is the
    case where that matters most (Gulf and Kazakh crude, African LNG). This quantifies the
    blind spot for the whole node set and for one focus economy.

    Args:
        products: HS prefixes defining the restricted scope (default ``config.HS_ENERGY``).
        focus_iso3: Second importer to report alongside the whole node set.
        countries: The node set.
        labels: Names for the unrestricted and restricted scopes.

    Returns:
        DataFrame ``[scope, importer, imports_world_kusd, imports_within_kusd, intra_share]``
        with one row per (scope, importer) pair.
    """
    paths = data_loader.find_baci_files()
    trade = data_loader.load_baci(paths["trade"])
    country_codes = data_loader.load_country_codes(paths["country_codes"])
    trade = data_loader.attach_iso3(trade, country_codes)
    return sourcing_summary(
        trade, products=products, focus_iso3=focus_iso3, countries=countries, labels=labels
    )


def sourcing_summary(
    trade: pd.DataFrame,
    products: list[str] = config.HS_ENERGY,
    focus_iso3: str = "AUT",
    countries: list[str] = config.COUNTRIES,
    labels: tuple[str, str] = ("All merchandise", "Energy (HS-27)"),
) -> pd.DataFrame:
    """Inside-vs-outside import sourcing for an already-loaded, ISO3-attached trade frame.

    The pure core of :func:`import_sourcing` — see there for the interpretation.

    Args:
        trade: World-wide BACI rows with ``exporter_iso3``, ``importer_iso3``, ``k``, ``v``
            (i.e. the output of ``data_loader.attach_iso3``, *before* country filtering).
        products: HS prefixes defining the restricted scope.
        focus_iso3: Second importer to report alongside the whole node set.
        countries: The node set.
        labels: Names for the unrestricted and restricted scopes.

    Returns:
        DataFrame ``[scope, importer, imports_world_kusd, imports_within_kusd, intra_share]``.
    """
    values = trade["v"].to_numpy(dtype=float)
    exporters = trade["exporter_iso3"].astype(str).to_numpy()
    importers = trade["importer_iso3"].astype(str).to_numpy()
    in_scope = trade["k"].str.startswith(tuple(products)).to_numpy(dtype=bool)
    exporter_inside = np.isin(exporters, countries)
    importer_inside = np.isin(importers, countries)
    is_focus = importers == focus_iso3
    # Self-trade never enters the graph, so exclude it from the reference total too.
    cross_border = exporters != importers

    rows: list[dict[str, str | float]] = []
    for scope, scope_mask in ((labels[0], np.ones_like(in_scope)), (labels[1], in_scope)):
        for importer, importer_mask in (
            (f"{len(countries)}-economy set", importer_inside),
            (focus_iso3, is_focus),
        ):
            selected = scope_mask & importer_mask & cross_border
            world = float(values[selected].sum())
            within = float(values[selected & exporter_inside].sum())
            rows.append(
                {
                    "scope": scope,
                    "importer": importer,
                    "imports_world_kusd": world,
                    "imports_within_kusd": within,
                    "intra_share": within / world if world > 0.0 else 0.0,
                }
            )
    return pd.DataFrame(rows)


def load_product_flows(
    products: list[str] = config.HS_ENERGY,
    level: int = 4,
) -> pd.DataFrame:
    """Load product-level flows inside the node set, aggregated to HS-``level`` codes.

    ``data_loader.build_edgelist`` sums over products; this keeps the product dimension so
    the composition of a chapter (crude vs gas vs electricity) can be read off.

    Args:
        products: HS prefixes to keep (default ``config.HS_ENERGY``).
        level: Number of HS digits to aggregate to (4 = heading).

    Returns:
        DataFrame ``[exporter_iso3, importer_iso3, hs, value_kusd]``, self-loops dropped.
    """
    paths = data_loader.find_baci_files()
    trade = data_loader.load_baci(paths["trade"])
    country_codes = data_loader.load_country_codes(paths["country_codes"])
    trade = data_loader.attach_iso3(trade, country_codes)
    trade = data_loader.filter_countries(trade)
    trade = data_loader.filter_products(trade, products)
    trade = trade.assign(hs=trade["k"].str[:level])
    flows = trade.groupby(["exporter_iso3", "importer_iso3", "hs"], as_index=False).agg(
        value_kusd=("v", "sum")
    )
    flows = flows.loc[flows["exporter_iso3"] != flows["importer_iso3"]]
    return flows.reset_index(drop=True)


def heading_composition(
    flows: pd.DataFrame,
    iso3: str | None = None,
    direction: str = "total",
) -> pd.DataFrame:
    """What the energy trade is made of, by HS heading.

    Args:
        flows: Product-level flows from :func:`load_product_flows`.
        iso3: Restrict to one economy's trade; ``None`` = the whole network.
        direction: ``"exports"``, ``"imports"``, or ``"total"`` (both directions).
            Ignored when ``iso3`` is ``None``.

    Returns:
        DataFrame ``[hs, heading, value_kusd, share]`` sorted by value, largest first.

    Raises:
        ValueError: If ``direction`` is not one of ``"total"``, ``"exports"``, ``"imports"``.
    """
    if direction not in _DIRECTIONS:
        raise ValueError(f"unknown direction '{direction}' — expected one of {_DIRECTIONS}")

    count_exports = direction in ("exports", "total")
    count_imports = direction in ("imports", "total")

    totals: dict[str, float] = {}
    for exporter, importer, hs, value in flows[
        ["exporter_iso3", "importer_iso3", "hs", "value_kusd"]
    ].itertuples(index=False, name=None):
        if iso3 is not None and not (
            (count_exports and str(exporter) == iso3) or (count_imports and str(importer) == iso3)
        ):
            continue
        totals[str(hs)] = totals.get(str(hs), 0.0) + float(value)
    codes = sorted(totals)
    values = [totals[hs] for hs in codes]
    total = sum(values)
    composition = pd.DataFrame(
        {
            "hs": codes,
            "heading": [HS27_HEADINGS.get(hs, hs) for hs in codes],
            "value_kusd": values,
            "share": [v / total if total > 0.0 else 0.0 for v in values],
        }
    )
    return composition.sort_values("value_kusd", ascending=False).reset_index(drop=True)
