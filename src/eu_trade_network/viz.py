"""Plotly / PyVis / Matplotlib figures. Headline PNGs go to figures/headline/."""

from __future__ import annotations

from pathlib import Path

import networkx as nx
import pandas as pd
import plotly.graph_objects as go

from . import config


def plot_flow_map(edgelist: pd.DataFrame, node_meta: pd.DataFrame, top_n: int = 150) -> go.Figure:
    """Scattergeo hero map: nodes at lat/lon, the ``top_n`` edges by value as lines.

    Args:
        edgelist: Bilateral edges with ``exporter_iso3``, ``importer_iso3``, ``value_kusd``.
        node_meta: Node table with at least ``iso3``, ``lat``, ``lon`` (and optionally
            ``name`` for hover/labels).
        top_n: Number of highest-value edges to draw.

    Returns:
        Plotly figure ready for display or ``save_fig``.
    """
    required_edge = {"exporter_iso3", "importer_iso3", "value_kusd"}
    missing_edge = required_edge - set(edgelist.columns)
    if missing_edge:
        raise ValueError(f"edgelist missing columns: {sorted(missing_edge)}")

    required_node = {"iso3", "lat", "lon"}
    missing_node = required_node - set(node_meta.columns)
    if missing_node:
        raise ValueError(f"node_meta missing columns: {sorted(missing_node)}")

    coords = {
        str(iso3): (float(lat), float(lon))
        for iso3, lat, lon in node_meta[["iso3", "lat", "lon"]].itertuples(index=False, name=None)
    }
    top = edgelist.nlargest(top_n, "value_kusd")
    max_val = float(top["value_kusd"].to_numpy().max()) if len(top) else 1.0

    fig = go.Figure()

    for exporter, importer, value in top[
        ["exporter_iso3", "importer_iso3", "value_kusd"]
    ].itertuples(index=False, name=None):
        exp = str(exporter)
        imp = str(importer)
        if exp not in coords or imp not in coords:
            continue
        lat0, lon0 = coords[exp]
        lat1, lon1 = coords[imp]
        width = 0.4 + 3.5 * (float(value) / max_val)
        fig.add_trace(
            go.Scattergeo(
                lon=[lon0, lon1, None],
                lat=[lat0, lat1, None],
                mode="lines",
                line={"width": width, "color": "rgba(40, 80, 140, 0.45)"},
                hoverinfo="skip",
                showlegend=False,
            )
        )

    if "name" in node_meta.columns:
        labels = node_meta["name"].astype(str).tolist()
    else:
        labels = node_meta["iso3"].astype(str).tolist()
    fig.add_trace(
        go.Scattergeo(
            lon=node_meta["lon"].astype(float).tolist(),
            lat=node_meta["lat"].astype(float).tolist(),
            text=labels,
            mode="markers+text",
            marker={
                "size": 8,
                "color": "#c0392b",
                "line": {"width": 0.5, "color": "white"},
            },
            textposition="top center",
            textfont={"size": 9},
            hovertemplate="%{text}<extra></extra>",
            name="Economies",
        )
    )

    fig.update_geos(
        projection_type="natural earth",
        showcountries=True,
        countrycolor="rgba(120, 120, 120, 0.4)",
        showland=True,
        landcolor="rgb(245, 245, 240)",
        showocean=True,
        oceancolor="rgb(220, 232, 242)",
        lataxis_range=[-10, 75],
        lonaxis_range=[-130, 150],
    )
    fig.update_layout(
        title=f"European merchandise trade flows (top {top_n} edges)",
        margin={"l": 10, "r": 10, "t": 50, "b": 10},
        height=620,
        showlegend=False,
    )
    return fig


def plot_lonlat_flows(
    edgelist: pd.DataFrame, node_meta: pd.DataFrame, top_n: int = 150, title: str | None = None
) -> go.Figure:
    """Lon/lat flow map using Cartesian axes (kaleido-safe; no Plotly topojson CDN).

    Args:
        edgelist: Bilateral edges with ``exporter_iso3``, ``importer_iso3``, ``value_kusd``.
        node_meta: Node table with ``iso3``, ``lat``, ``lon`` (optional ``name``).
        top_n: Number of highest-value edges to draw.
        title: Optional figure title.

    Returns:
        Plotly figure ready for display or ``save_fig``.
    """
    required_edge = {"exporter_iso3", "importer_iso3", "value_kusd"}
    missing_edge = required_edge - set(edgelist.columns)
    if missing_edge:
        raise ValueError(f"edgelist missing columns: {sorted(missing_edge)}")

    required_node = {"iso3", "lat", "lon"}
    missing_node = required_node - set(node_meta.columns)
    if missing_node:
        raise ValueError(f"node_meta missing columns: {sorted(missing_node)}")

    coords = {
        str(iso3): (float(lat), float(lon))
        for iso3, lat, lon in node_meta[["iso3", "lat", "lon"]].itertuples(index=False, name=None)
    }
    top = edgelist.nlargest(top_n, "value_kusd")
    max_val = float(top["value_kusd"].to_numpy().max()) if len(top) else 1.0

    fig = go.Figure()
    for exporter, importer, value in top[
        ["exporter_iso3", "importer_iso3", "value_kusd"]
    ].itertuples(index=False, name=None):
        exp = str(exporter)
        imp = str(importer)
        if exp not in coords or imp not in coords:
            continue
        lat0, lon0 = coords[exp]
        lat1, lon1 = coords[imp]
        width = 0.4 + 3.5 * (float(value) / max_val)
        fig.add_trace(
            go.Scatter(
                x=[lon0, lon1, None],
                y=[lat0, lat1, None],
                mode="lines",
                line={"width": width, "color": "rgba(40, 80, 140, 0.45)"},
                hoverinfo="skip",
                showlegend=False,
            )
        )

    if "name" in node_meta.columns:
        labels = node_meta["name"].astype(str).tolist()
    else:
        labels = node_meta["iso3"].astype(str).tolist()
    fig.add_trace(
        go.Scatter(
            x=node_meta["lon"].astype(float).tolist(),
            y=node_meta["lat"].astype(float).tolist(),
            text=labels,
            mode="markers+text",
            marker={
                "size": 8,
                "color": "#c0392b",
                "line": {"width": 0.5, "color": "white"},
            },
            textposition="top center",
            textfont={"size": 9},
            hovertemplate="%{text}<extra></extra>",
            name="Economies",
        )
    )
    fig.update_layout(
        title=title or f"Trade flows (top {top_n} edges)",
        xaxis_title="Longitude",
        yaxis_title="Latitude",
        xaxis={"range": [-130, 150]},
        yaxis={"range": [-10, 75], "scaleanchor": "x", "scaleratio": 1},
        margin={"l": 40, "r": 20, "t": 50, "b": 40},
        height=620,
        showlegend=False,
        plot_bgcolor="rgb(245, 245, 240)",
    )
    return fig


def plot_degree_distribution(strength: pd.DataFrame) -> go.Figure:
    """Strength distribution (this network is dense — do NOT force a power-law fit).

    Args:
        strength: DataFrame with ``iso3`` and at least one of ``out_strength``,
            ``in_strength``, or ``strength``. Prefer ``out_strength`` (exports).

    Returns:
        Plotly bar/scatter figure of node strength (no power-law overlay).
    """
    frame = strength.copy()
    if "out_strength" in frame.columns:
        value_col = "out_strength"
        label = "Out-strength (exports, thousand USD)"
    elif "strength" in frame.columns:
        value_col = "strength"
        label = "Strength (thousand USD)"
    elif "in_strength" in frame.columns:
        value_col = "in_strength"
        label = "In-strength (imports, thousand USD)"
    else:
        raise ValueError("strength must include 'out_strength', 'in_strength', or 'strength'")

    ranked = frame.sort_values(value_col, ascending=False).reset_index(drop=True)
    ranked["rank"] = ranked.index + 1
    hover = ranked["iso3"].astype(str) if "iso3" in ranked.columns else ranked["rank"].astype(str)

    fig = go.Figure(
        data=[
            go.Scatter(
                x=ranked["rank"],
                y=ranked[value_col],
                mode="markers+lines",
                marker={"size": 9, "color": "#1f4e79"},
                line={"width": 1.2, "color": "rgba(31, 78, 121, 0.45)"},
                text=hover,
                hovertemplate="%{text}<br>rank=%{x}<br>strength=%{y:,.0f}<extra></extra>",
            )
        ]
    )
    fig.update_layout(
        title=(
            "Node strength distribution — dense trade graph "
            "(no power-law fit; scale-free framing does not apply)"
        ),
        xaxis_title="Rank (1 = largest)",
        yaxis_title=label,
        yaxis_type="log",
        margin={"l": 60, "r": 20, "t": 70, "b": 50},
        height=480,
        annotations=[
            {
                "text": (
                    "Near-complete bilateral coverage ⇒ high density; "
                    "use the disparity-filter backbone for structure."
                ),
                "xref": "paper",
                "yref": "paper",
                "x": 0.5,
                "y": -0.18,
                "showarrow": False,
                "font": {"size": 11, "color": "#555"},
            }
        ],
    )
    return fig


def plot_network_pyvis(undirected: nx.Graph, partition: dict[str, int], out_html: Path) -> None:
    """Interactive PyVis network: node size = strength, colour = community."""
    raise NotImplementedError("TODO: implement in Cursor Prompt P4")


def plot_resilience(curves: pd.DataFrame) -> go.Figure:
    """Targeted vs random removal curves (LCC fraction and trade retained)."""
    raise NotImplementedError("TODO: implement in Cursor Prompt P5")


def save_fig(
    fig: go.Figure,
    name: str,
    headline: bool = True,
    headline_dir: Path = config.HEADLINE_FIG_DIR,
    qa_dir: Path = config.QA_FIG_DIR,
) -> Path:
    """Write a figure to ``headline_dir`` (committed) or ``qa_dir`` (gitignored) as PNG.

    Args:
        fig: Plotly figure.
        name: Filename stem or ``.png`` name.
        headline: If True, write under ``headline_dir``; else ``qa_dir``.
        headline_dir: Committed figures directory.
        qa_dir: Gitignored QA figures directory.

    Returns:
        Path of the written PNG.
    """
    out_dir = Path(headline_dir) if headline else Path(qa_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    filename = name if name.endswith(".png") else f"{name}.png"
    path = out_dir / filename
    fig.write_image(str(path), scale=2)
    return path
