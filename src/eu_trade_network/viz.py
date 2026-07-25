"""Plotly / PyVis / Matplotlib figures. Headline PNGs go to figures/headline/.

Figures are styled for a **dark Quarto website**: charcoal paper, light ink,
Okabe–Ito categorical colours, and transparent-friendly legend boxes.

Hub ISO3 labels are placed by :func:`_place_labels`, a small deterministic
greedy solver (a miniature of textalloc / D3-Labeler; Plotly has no native
label de-overlap — see plotly.js#4674). For each label it sweeps candidate
boxes on rings around the node and keeps the lowest-cost slot that stays on the
canvas and off other nodes / already-placed labels, then draws a leader line.
This replaces brittle hand-tuned per-country offsets and keeps distant hubs
(USA, RUS, JPN) inside the frame automatically.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import networkx as nx
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from . import config

# ---------------------------------------------------------------------------
# Dark Quarto theme (Okabe–Ito categorical accents)
# ---------------------------------------------------------------------------

_PAPER = "#12141a"
_PLOT = "#1a1d26"
_INK = "#e8eaed"
_MUTED = "#b4b9c2"
_GRID = "rgba(255,255,255,0.07)"
_EDGE = "rgba(86, 180, 233, {alpha:.3f})"  # Okabe–Ito sky blue
_EU = "#56B4E9"  # sky blue
_PARTNER = "#E69F00"  # orange
_MARKER_LINE = "#12141a"
_ACCENT = "#56B4E9"
_FONT_FAMILY = "IBM Plex Sans, Arial, sans-serif"

# Legible, harmonised type scale (px) shared by every figure.
_FS_BASE = 15
_FS_TICK = 13
_FS_AXIS = 15
_FS_TITLE = 19
_FS_SUBTITLE = 15
_FS_LEGEND = 13
_FS_LABEL = 13
_FS_FOOT = 12.5

# Pinned backbone figure geometry (label pixel offsets depend on it).
_BB_W = 1240
_BB_H = 600
_BB_MARGIN = {"l": 60, "r": 30, "t": 92, "b": 96}


def _dark_layout(**extra: Any) -> dict[str, Any]:
    """Shared layout kwargs for dark Quarto figures."""
    base: dict[str, Any] = {
        "template": "plotly_dark",
        "paper_bgcolor": _PAPER,
        "plot_bgcolor": _PLOT,
        "font": {"color": _INK, "family": _FONT_FAMILY, "size": _FS_BASE},
        "title": {"font": {"size": _FS_TITLE, "color": _INK}, "x": 0.01, "xanchor": "left"},
        "legend": {
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
            "xanchor": "right",
            "x": 1.0,
            "bgcolor": "rgba(18,20,26,0.55)",
            "bordercolor": "rgba(255,255,255,0.12)",
            "borderwidth": 1,
            "font": {"color": _INK, "size": _FS_LEGEND},
        },
        "hoverlabel": {
            "bgcolor": "#2a2f3a",
            "bordercolor": _MUTED,
            "font": {"color": _INK, "family": _FONT_FAMILY, "size": _FS_TICK},
        },
    }
    base.update(extra)
    return base


def _axis_dark(**extra: Any) -> dict[str, Any]:
    """Shared Cartesian axis styling for dark figures."""
    base: dict[str, Any] = {
        "zeroline": False,
        "showgrid": True,
        "gridcolor": _GRID,
        "gridwidth": 1,
        "color": _MUTED,
        "title": {"font": {"color": _INK, "size": _FS_AXIS}},
        "tickfont": {"color": _MUTED, "size": _FS_TICK},
        "automargin": True,
        "fixedrange": True,
    }
    base.update(extra)
    return base


def _footnote(text: str, *, y: float = -0.16) -> dict[str, Any]:
    """Paper-relative caption under the plot."""
    return {
        "text": text,
        "xref": "paper",
        "yref": "paper",
        "x": 0.5,
        "y": y,
        "showarrow": False,
        "font": {"size": _FS_FOOT, "color": _MUTED},
        "align": "center",
    }


def _place_labels(
    labels: list[dict[str, Any]],
    *,
    x_range: tuple[float, float],
    y_range: tuple[float, float],
    fig_w: int,
    fig_h: int,
    margin: dict[str, int],
    x_domain: tuple[float, float] = (0.0, 1.0),
    y_domain: tuple[float, float] = (0.0, 1.0),
    xref: str = "x",
    yref: str = "y",
    obstacles: tuple[tuple[float, float], ...] = (),
    radii: tuple[float, ...] = (34.0, 52.0, 74.0, 100.0, 130.0),
    angles: tuple[float, ...] = (90, 45, 135, 0, 180, -45, -135, -90),
    char_w: float = 8.2,
    line_h: float = 17.0,
) -> list[dict[str, Any]]:
    """Greedy non-overlapping ISO3 label placement → Plotly annotation dicts.

    A miniature textalloc / D3-Labeler: for each label (in the given order) it
    sweeps candidate box centres on ``radii × angles`` around the node and keeps
    the lowest-cost slot, scoring off-canvas overrun, overlap with obstacle
    markers, and overlap area with already-placed labels. The chosen slot's
    pixel offset drives ``ax``/``ay`` so the leader line ties to the label.

    Pixel geometry must match the rendered figure, so ``fig_w``/``fig_h``/
    ``margin`` (and the subplot ``x_domain``/``y_domain``) are required and the
    figure size must be pinned.

    Args:
        labels: Dicts with ``x``, ``y`` (data coords) and ``text`` (ISO3).
        x_range: Axis x data range ``(min, max)``.
        y_range: Axis y data range ``(min, max)``.
        fig_w: Figure width in px (must match ``update_layout(width=…)``).
        fig_h: Figure height in px.
        margin: ``{"l","r","t","b"}`` margins in px.
        x_domain: Subplot x paper-fraction domain ``(start, end)``.
        y_domain: Subplot y paper-fraction domain ``(bottom, top)``.
        xref: Plotly x reference for the annotation anchor (``x`` / ``x2`` …).
        yref: Plotly y reference for the annotation anchor.
        obstacles: ``(x, y)`` data coords of markers labels should avoid.
        radii: Candidate ring radii in px, nearest first.
        angles: Candidate angles in degrees (``90`` = above the node).
        char_w: Approx per-character label width in px (box sizing).
        line_h: Approx line height in px (box sizing).

    Returns:
        Plotly annotation dicts for ``fig.add_annotation`` / layout.
    """
    pw = fig_w - margin["l"] - margin["r"]
    ph = fig_h - margin["t"] - margin["b"]
    sx0 = margin["l"] + x_domain[0] * pw
    sx1 = margin["l"] + x_domain[1] * pw
    sy_top = margin["t"] + (1.0 - y_domain[1]) * ph
    sy_bot = margin["t"] + (1.0 - y_domain[0]) * ph
    (x0, x1), (y0, y1) = x_range, y_range

    def to_px(x: float, y: float) -> tuple[float, float]:
        px = sx0 + (x - x0) / (x1 - x0) * (sx1 - sx0)
        py = sy_top + (1.0 - (y - y0) / (y1 - y0)) * (sy_bot - sy_top)
        return px, py

    obstacle_px = [to_px(ox, oy) for ox, oy in obstacles]
    placed: list[tuple[float, float, float, float]] = []
    edge_pad = 6.0
    obstacle_pad = 6.0
    w_edge = 4.0
    w_obstacle = 45.0
    w_label = 0.02

    def cost(cx: float, cy: float, bw: float, bh: float) -> float:
        left, right = cx - bw / 2, cx + bw / 2
        top, bottom = cy - bh / 2, cy + bh / 2
        c = 0.0
        c += w_edge * (max(0.0, (sx0 + edge_pad) - left) + max(0.0, right - (sx1 - edge_pad)))
        c += w_edge * (max(0.0, (sy_top + edge_pad) - top) + max(0.0, bottom - (sy_bot - edge_pad)))
        for mx, my in obstacle_px:
            if left - obstacle_pad <= mx <= right + obstacle_pad and (
                top - obstacle_pad <= my <= bottom + obstacle_pad
            ):
                c += w_obstacle
        for ox, oy, ow, oh in placed:
            ix = max(0.0, min(right, ox + ow / 2) - max(left, ox - ow / 2))
            iy = max(0.0, min(bottom, oy + oh / 2) - max(top, oy - oh / 2))
            c += ix * iy * w_label
        return c

    annotations: list[dict[str, Any]] = []
    for lab in labels:
        text = str(lab["text"])
        bw = len(text) * char_w + 12.0
        bh = line_h + 8.0
        px, py = to_px(float(lab["x"]), float(lab["y"]))
        best: tuple[float, float, float] | None = None
        for r in radii:
            for a in angles:
                cx = px + r * math.cos(math.radians(a))
                cy = py - r * math.sin(math.radians(a))
                c = cost(cx, cy, bw, bh)
                if best is None or c < best[0]:
                    best = (c, cx, cy)
                if c == 0.0:
                    break
            if best is not None and best[0] == 0.0:
                break
        assert best is not None
        _, cx, cy = best
        placed.append((cx, cy, bw, bh))
        annotations.append(
            {
                "x": float(lab["x"]),
                "y": float(lab["y"]),
                "xref": xref,
                "yref": yref,
                "ax": cx - px,
                "ay": cy - py,
                "axref": "pixel",
                "ayref": "pixel",
                "text": text,
                "showarrow": True,
                "arrowhead": 0,
                "arrowwidth": 0.9,
                "arrowcolor": "rgba(232,234,237,0.45)",
                "font": {"size": _FS_LABEL, "color": _INK, "family": _FONT_FAMILY},
                "bgcolor": "rgba(18,20,26,0.78)",
                "bordercolor": "rgba(255,255,255,0.16)",
                "borderwidth": 1,
                "borderpad": 2,
                "align": "center",
            }
        )
    return annotations


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

    meta = node_meta.copy().reset_index(drop=True)
    meta["iso3"] = meta["iso3"].astype(str)
    coords = {
        str(iso3): (float(lat), float(lon))
        for iso3, lat, lon in meta[["iso3", "lat", "lon"]].itertuples(index=False, name=None)
    }
    top = edgelist.nlargest(top_n, "value_kusd").sort_values("value_kusd", ascending=True)
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
        share = float(value) / max_val
        width = 0.35 + 2.2 * (share**0.7)
        alpha = 0.12 + 0.40 * (share**0.7)
        fig.add_trace(
            go.Scattergeo(
                lon=[lon0, lon1, None],
                lat=[lat0, lat1, None],
                mode="lines",
                line={"width": width, "color": _EDGE.format(alpha=alpha)},
                hoverinfo="skip",
                showlegend=False,
            )
        )

    if "out_strength" in meta.columns:
        raw_s = meta.set_index("iso3")["out_strength"]
        strength = pd.Series(
            raw_s.to_numpy(dtype=float),
            index=raw_s.index.astype(str).tolist(),
            dtype=float,
        )
        hubs = {str(x) for x in strength.nlargest(6).index} | {
            "AUT",
            "USA",
            "CHN",
            "JPN",
            "GBR",
            "RUS",
        }
    else:
        hubs = {"AUT", "USA", "CHN", "JPN", "GBR", "RUS", "DEU", "FRA"}
    hubs &= {str(x) for x in meta["iso3"].tolist()}

    names = (
        meta["name"].astype(str).tolist()
        if "name" in meta.columns
        else meta["iso3"].astype(str).tolist()
    )
    hover = [f"{n} ({i})" for n, i in zip(names, meta["iso3"].astype(str), strict=True)]

    if "grp" in meta.columns:
        groups = [
            ("EU", _EU, meta.loc[meta["grp"].astype(str) == "EU"]),
            ("Partner", _PARTNER, meta.loc[meta["grp"].astype(str) != "EU"]),
        ]
    else:
        groups = [("Economies", _PARTNER, meta)]

    for legend_name, color, frame in groups:
        if frame.empty:
            continue
        fig.add_trace(
            go.Scattergeo(
                lon=frame["lon"].astype(float).tolist(),
                lat=frame["lat"].astype(float).tolist(),
                mode="markers",
                name=legend_name,
                marker={
                    "size": 8,
                    "color": color,
                    "line": {"width": 0.6, "color": _MARKER_LINE},
                    "opacity": 0.95,
                },
                customdata=[hover[int(i)] for i in frame.index.to_numpy()],
                hovertemplate="%{customdata}<extra></extra>",
            )
        )

    # Geo text labels (hub ISO3 only) — scattergeo textposition is coarse, so
    # keep the set small and offset via textposition heuristics.
    hub_frame = meta.loc[meta["iso3"].isin(sorted(hubs))]
    geo_pos = {
        "USA": "middle left",
        "CHN": "top center",
        "JPN": "middle right",
        "RUS": "top right",
        "GBR": "top left",
        "DEU": "bottom center",
        "FRA": "middle left",
        "AUT": "bottom right",
    }
    fig.add_trace(
        go.Scattergeo(
            lon=hub_frame["lon"].astype(float).tolist(),
            lat=hub_frame["lat"].astype(float).tolist(),
            text=hub_frame["iso3"].astype(str).tolist(),
            mode="text",
            showlegend=False,
            textposition=[geo_pos.get(str(i), "top center") for i in hub_frame["iso3"]],
            textfont={"size": _FS_LABEL, "color": _INK, "family": "IBM Plex Sans, Arial"},
            hoverinfo="skip",
        )
    )

    fig.update_geos(
        projection_type="natural earth",
        showcountries=True,
        countrycolor="rgba(255,255,255,0.18)",
        showland=True,
        landcolor="#252a35",
        showocean=True,
        oceancolor="#0e1016",
        showlakes=False,
        showframe=False,
        bgcolor=_PAPER,
        lataxis_range=[-10, 75],
        lonaxis_range=[-130, 150],
    )
    fig.update_layout(
        **_dark_layout(
            title={
                "text": f"European merchandise trade flows (top {top_n} edges)",
                "x": 0.01,
                "xanchor": "left",
                "font": {"size": _FS_TITLE, "color": _INK},
            },
            margin={"l": 10, "r": 10, "t": 60, "b": 10},
            height=620,
            showlegend=True,
        )
    )
    return fig


def plot_lonlat_flows(
    edgelist: pd.DataFrame,
    node_meta: pd.DataFrame,
    top_n: int = 150,
    title: str | None = None,
    *,
    label_iso3: bool = True,
    label_top_n: int = 6,
    always_label: tuple[str, ...] | None = None,
) -> go.Figure:
    """Lon/lat trade-flow map on Cartesian axes (kaleido-safe; no topojson CDN).

    Tuned for a dense European core plus distant partners: wide aspect matching
    the lon≫lat span, short ISO3 hub labels only, strength-scaled markers, and
    thin translucent edges (weakest first so strong links sit on top).

    Args:
        edgelist: Bilateral edges with ``exporter_iso3``, ``importer_iso3``, ``value_kusd``.
        node_meta: Node table with ``iso3``, ``lat``, ``lon``; optional ``name``,
            ``grp``, ``out_strength``.
        top_n: Number of highest-value edges to draw.
        title: Optional figure title.
        label_iso3: If True, label hubs with ISO3 codes (not full names).
        label_top_n: Label this many largest exporters (by ``out_strength`` if
            present, else equal size).
        always_label: Extra ISO3 codes always labelled (defaults to Austria +
            major extra-EU partners).

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

    meta = node_meta.copy().reset_index(drop=True)
    meta["iso3"] = meta["iso3"].astype(str)
    coords = {
        str(iso3): (float(lat), float(lon))
        for iso3, lat, lon in meta[["iso3", "lat", "lon"]].itertuples(index=False, name=None)
    }

    if always_label is None:
        always_label = ("AUT", "USA", "CHN", "JPN", "GBR", "RUS")

    if "out_strength" in meta.columns:
        raw = meta.set_index("iso3")["out_strength"]
        strength = pd.Series(
            raw.to_numpy(dtype=float),
            index=raw.index.astype(str).tolist(),
            dtype=float,
        )
    else:
        strength = pd.Series(
            [1.0] * len(meta),
            index=meta["iso3"].astype(str).tolist(),
            dtype=float,
        )

    hub_iso3: set[str] = {str(x) for x in strength.nlargest(label_top_n).index} | {
        str(x) for x in always_label
    }
    hub_iso3 &= {str(x) for x in meta["iso3"].tolist()}

    top = edgelist.nlargest(top_n, "value_kusd").sort_values("value_kusd", ascending=True)
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
        share = float(value) / max_val
        width = 0.3 + 1.6 * (share**0.7)
        alpha = 0.10 + 0.38 * (share**0.7)
        fig.add_trace(
            go.Scatter(
                x=[lon0, lon1, None],
                y=[lat0, lat1, None],
                mode="lines",
                line={"width": width, "color": _EDGE.format(alpha=alpha)},
                hoverinfo="skip",
                showlegend=False,
            )
        )

    strength_aligned = strength.reindex(meta["iso3"].astype(str))
    s_med = float(strength.to_numpy(dtype=float).mean())
    s_vals = strength_aligned.fillna(s_med).to_numpy(dtype=float)
    s_max = float(s_vals.max()) if len(s_vals) else 1.0
    sizes = (8.0 + 16.0 * (s_vals / s_max) ** 0.5).tolist()

    names = (
        meta["name"].astype(str).tolist()
        if "name" in meta.columns
        else meta["iso3"].astype(str).tolist()
    )
    hover = [f"{n} ({i})" for n, i in zip(names, meta["iso3"].astype(str), strict=True)]

    def _add_group(frame: pd.DataFrame, color: str, legend_name: str) -> None:
        if frame.empty:
            return
        sub_idx = frame.index.to_numpy()
        fig.add_trace(
            go.Scatter(
                x=frame["lon"].astype(float).tolist(),
                y=frame["lat"].astype(float).tolist(),
                mode="markers",
                name=legend_name,
                legendgroup=legend_name,
                marker={
                    "size": [sizes[int(i)] for i in sub_idx],
                    "color": color,
                    "line": {"width": 0.7, "color": _MARKER_LINE},
                    "opacity": 0.95,
                },
                customdata=[hover[int(i)] for i in sub_idx],
                hovertemplate="%{customdata}<extra></extra>",
            )
        )

    if "grp" in meta.columns:
        _add_group(meta.loc[meta["grp"].astype(str) == "EU"], _EU, "EU")
        _add_group(meta.loc[meta["grp"].astype(str) != "EU"], _PARTNER, "Partner")
    else:
        _add_group(meta, _PARTNER, "Economies")

    lon_min = float(meta["lon"].to_numpy(dtype=float).min())
    lon_max = float(meta["lon"].to_numpy(dtype=float).max())
    lat_min = float(meta["lat"].to_numpy(dtype=float).min())
    lat_max = float(meta["lat"].to_numpy(dtype=float).max())
    x_range = (lon_min - 10.0, lon_max + 10.0)
    y_range = (lat_min - 4.0, lat_max + 6.0)

    fig_w, fig_h = 1120, 540
    margin = {"l": 70, "r": 30, "t": 70, "b": 100}

    strength_map = {str(k): float(v) for k, v in strength.items()}
    annotations: list[dict[str, Any]] = []
    if label_iso3:
        # Greedy solver keeps distant hubs (USA/RUS/JPN) inside the frame and
        # spreads the dense EU core automatically — no per-country offsets.
        by_iso = meta.set_index("iso3")
        labels = [
            {"x": float(by_iso.loc[iso, "lon"]), "y": float(by_iso.loc[iso, "lat"]), "text": iso}
            for iso in sorted(hub_iso3, key=lambda i: strength_map.get(i, 0.0), reverse=True)
        ]
        obstacles = tuple(
            (float(lon), float(lat))
            for lon, lat in meta[["lon", "lat"]].itertuples(index=False, name=None)
        )
        annotations.extend(
            _place_labels(
                labels,
                x_range=x_range,
                y_range=y_range,
                fig_w=fig_w,
                fig_h=fig_h,
                margin=margin,
                obstacles=obstacles,
            )
        )
    annotations.append(
        _footnote(
            "Node size ∝ export strength · ISO3 = hubs only · edge opacity/width ∝ trade value",
            y=-0.20,
        )
    )

    fig.update_layout(
        **_dark_layout(
            title={
                "text": title or f"Trade flows (top {top_n} edges)",
                "x": 0.02,
                "xanchor": "left",
                "font": {"size": _FS_TITLE, "color": _INK},
            },
            xaxis=_axis_dark(title={"text": "Longitude"}, range=list(x_range)),
            yaxis=_axis_dark(title={"text": "Latitude"}, range=list(y_range)),
            margin=margin,
            height=fig_h,
            width=fig_w,
            showlegend=True,
            annotations=annotations,
        )
    )
    return fig


def plot_backbone_map(
    edgelist: pd.DataFrame,
    node_meta: pd.DataFrame,
    title: str | None = None,
) -> go.Figure:
    """Two-panel disparity-filter backbone map for the headline figure.

    Left: Europe zoom (readable hub structure). Right: global context so USA /
    China / Japan remain visible. Kaleido-safe Cartesian axes (no topojson CDN).
    Hub ISO3 labels use annotation offsets + leader lines to avoid collisions.

    Args:
        edgelist: Backbone edges with ``exporter_iso3``, ``importer_iso3``, ``value_kusd``.
        node_meta: Nodes with ``iso3``, ``lat``, ``lon``; ideally ``grp``, ``out_strength``,
            ``name``.
        title: Optional overall title.

    Returns:
        Plotly figure ready for ``save_fig``.
    """
    required_edge = {"exporter_iso3", "importer_iso3", "value_kusd"}
    missing_edge = required_edge - set(edgelist.columns)
    if missing_edge:
        raise ValueError(f"edgelist missing columns: {sorted(missing_edge)}")
    required_node = {"iso3", "lat", "lon"}
    missing_node = required_node - set(node_meta.columns)
    if missing_node:
        raise ValueError(f"node_meta missing columns: {sorted(missing_node)}")

    meta = node_meta.copy().reset_index(drop=True)
    meta["iso3"] = meta["iso3"].astype(str)
    coords = {
        str(iso3): (float(lat), float(lon))
        for iso3, lat, lon in meta[["iso3", "lat", "lon"]].itertuples(index=False, name=None)
    }

    if "out_strength" in meta.columns:
        raw = meta.set_index("iso3")["out_strength"]
        strength = pd.Series(
            raw.to_numpy(dtype=float),
            index=raw.index.astype(str).tolist(),
            dtype=float,
        )
    else:
        strength = pd.Series(
            [1.0] * len(meta),
            index=meta["iso3"].astype(str).tolist(),
            dtype=float,
        )

    s_aligned = strength.reindex(meta["iso3"].astype(str))
    s_med = float(strength.to_numpy(dtype=float).mean())
    s_vals = s_aligned.fillna(s_med).to_numpy(dtype=float)
    s_max = float(s_vals.max()) if len(s_vals) else 1.0
    sizes = (7.0 + 14.0 * (s_vals / s_max) ** 0.5).tolist()

    edges = edgelist.sort_values("value_kusd", ascending=True)
    max_val = float(edges["value_kusd"].to_numpy().max()) if len(edges) else 1.0

    names = (
        meta["name"].astype(str).tolist()
        if "name" in meta.columns
        else meta["iso3"].astype(str).tolist()
    )
    hover = [f"{n} ({i})" for n, i in zip(names, meta["iso3"].astype(str), strict=True)]

    # Structural hubs + AUT. Drop BEL/CHE/NOR/NLD — Benelux sits inside the
    # DEU knot and label boxes collide even with large offsets.
    europe_hubs = {
        "DEU",
        "FRA",
        "ITA",
        "ESP",
        "POL",
        "AUT",
        "GBR",
        "SWE",
        "TUR",
        "RUS",
    }
    world_hubs = {"USA", "CHN", "JPN", "RUS"}

    col_widths = (0.58, 0.42)
    hspace = 0.08
    fig = make_subplots(
        rows=1,
        cols=2,
        column_widths=list(col_widths),
        subplot_titles=("Europe (backbone detail)", "Global context"),
        horizontal_spacing=hspace,
    )
    # Subplot paper-fraction domains (mirrors plotly's make_subplots layout) so
    # the label solver's pixel geometry matches the render.
    _avail = 1.0 - hspace
    x_dom1 = (0.0, col_widths[0] * _avail)
    x_dom2 = (col_widths[0] * _avail + hspace, 1.0)
    y_dom1 = (0.0, 1.0)
    y_dom2 = (0.0, 1.0)

    def _draw_edges(
        row: int,
        col: int,
        *,
        lon_range: tuple[float, float] | None = None,
        lat_range: tuple[float, float] | None = None,
    ) -> None:
        for exporter, importer, value in edges[
            ["exporter_iso3", "importer_iso3", "value_kusd"]
        ].itertuples(index=False, name=None):
            exp, imp = str(exporter), str(importer)
            if exp not in coords or imp not in coords:
                continue
            lat0, lon0 = coords[exp]
            lat1, lon1 = coords[imp]
            if lon_range is not None and lat_range is not None:
                lo0, lo1 = lon_range
                la0, la1 = lat_range
                if not (
                    lo0 <= lon0 <= lo1
                    and lo0 <= lon1 <= lo1
                    and la0 <= lat0 <= la1
                    and la0 <= lat1 <= la1
                ):
                    continue
            share = float(value) / max_val
            width = 0.4 + 2.0 * (share**0.65)
            alpha = 0.14 + 0.42 * (share**0.65)
            fig.add_trace(
                go.Scatter(
                    x=[lon0, lon1, None],
                    y=[lat0, lat1, None],
                    mode="lines",
                    line={"width": width, "color": _EDGE.format(alpha=alpha)},
                    hoverinfo="skip",
                    showlegend=False,
                ),
                row=row,
                col=col,
            )

    def _draw_nodes(row: int, col: int) -> None:
        show_leg = row == 1 and col == 1
        groups: list[tuple[str, str, pd.DataFrame]]
        if "grp" in meta.columns:
            groups = [
                ("EU", _EU, meta.loc[meta["grp"].astype(str) == "EU"]),
                ("Partner", _PARTNER, meta.loc[meta["grp"].astype(str) != "EU"]),
            ]
        else:
            groups = [("Economies", _PARTNER, meta)]

        for legend_name, color, frame in groups:
            if frame.empty:
                continue
            sub_idx = frame.index.to_numpy()
            fig.add_trace(
                go.Scatter(
                    x=frame["lon"].astype(float).tolist(),
                    y=frame["lat"].astype(float).tolist(),
                    mode="markers",
                    name=legend_name,
                    legendgroup=legend_name,
                    showlegend=bool(show_leg),
                    marker={
                        "size": [sizes[int(i)] for i in sub_idx],
                        "color": color,
                        "line": {"width": 0.7, "color": _MARKER_LINE},
                        "opacity": 0.95,
                    },
                    customdata=[hover[int(i)] for i in sub_idx],
                    hovertemplate="%{customdata}<extra></extra>",
                ),
                row=row,
                col=col,
            )

    europe_lon = (-28.0, 55.0)
    europe_lat = (30.0, 75.0)
    _draw_edges(1, 1, lon_range=europe_lon, lat_range=europe_lat)
    _draw_nodes(1, 1)
    _draw_edges(1, 2)
    _draw_nodes(1, 2)

    fig.update_xaxes(
        **_axis_dark(
            title_text="Longitude",
            range=list(europe_lon),
        ),
        row=1,
        col=1,
    )
    fig.update_yaxes(
        **_axis_dark(
            title_text="Latitude",
            range=list(europe_lat),
        ),
        row=1,
        col=1,
    )
    lon_min = float(meta["lon"].to_numpy(dtype=float).min())
    lon_max = float(meta["lon"].to_numpy(dtype=float).max())
    lat_min = float(meta["lat"].to_numpy(dtype=float).min())
    lat_max = float(meta["lat"].to_numpy(dtype=float).max())
    fig.update_xaxes(
        **_axis_dark(
            title_text="Longitude",
            range=[lon_min - 12.0, lon_max + 10.0],
        ),
        row=1,
        col=2,
    )
    fig.update_yaxes(
        **_axis_dark(
            title_text="Latitude",
            range=[lat_min - 3.0, lat_max + 4.0],
        ),
        row=1,
        col=2,
    )

    world_lon = (lon_min - 12.0, lon_max + 10.0)
    world_lat = (lat_min - 3.0, lat_max + 4.0)

    n_edges = len(edgelist)
    fig.update_layout(
        **_dark_layout(
            title={
                "text": title
                or (
                    f"Disparity-filter backbone (α={config.DISPARITY_ALPHA}): "
                    f"{n_edges} significant edges"
                ),
                "x": 0.01,
                "xanchor": "left",
                "font": {"size": _FS_TITLE, "color": _INK},
            },
            height=_BB_H,
            width=_BB_W,
            margin=_BB_MARGIN,
            legend={
                "orientation": "h",
                "yanchor": "bottom",
                "y": 1.09,
                "xanchor": "right",
                "x": 1.0,
                "bgcolor": "rgba(18,20,26,0.55)",
                "bordercolor": "rgba(255,255,255,0.12)",
                "borderwidth": 1,
                "font": {"color": _INK, "size": _FS_LEGEND},
            },
        )
    )
    # Restyle the make_subplots panel titles for the dark theme.
    fig.update_annotations(font={"color": _INK, "size": _FS_SUBTITLE})

    # Auto-place hub labels per panel (domains computed above).
    strength_map = {str(k): float(v) for k, v in strength.items()}
    by_iso = meta.set_index("iso3")

    def _panel_labels(
        hubs: set[str],
        lon_range: tuple[float, float],
        lat_range: tuple[float, float],
        x_dom: tuple[float, float],
        y_dom: tuple[float, float],
        xref: str,
        yref: str,
    ) -> list[dict[str, Any]]:
        present = [h for h in hubs if h in by_iso.index]
        labels = [
            {"x": float(by_iso.loc[h, "lon"]), "y": float(by_iso.loc[h, "lat"]), "text": h}
            for h in sorted(present, key=lambda i: strength_map.get(i, 0.0), reverse=True)
        ]
        lo0, lo1 = lon_range
        la0, la1 = lat_range
        obstacles = tuple(
            (float(lon), float(lat))
            for lon, lat in meta[["lon", "lat"]].itertuples(index=False, name=None)
            if lo0 <= lon <= lo1 and la0 <= lat <= la1
        )
        return _place_labels(
            labels,
            x_range=lon_range,
            y_range=lat_range,
            fig_w=_BB_W,
            fig_h=_BB_H,
            margin=_BB_MARGIN,
            x_domain=x_dom,
            y_domain=y_dom,
            xref=xref,
            yref=yref,
            obstacles=obstacles,
        )

    for ann in _panel_labels(europe_hubs, europe_lon, europe_lat, x_dom1, y_dom1, "x", "y"):
        fig.add_annotation(**ann)
    for ann in _panel_labels(world_hubs, world_lon, world_lat, x_dom2, y_dom2, "x2", "y2"):
        fig.add_annotation(**ann)
    fig.add_annotation(
        **_footnote(
            "EU · sky blue Partners · orange · node size ∝ export strength · "
            "edge weight ∝ trade value",
            y=-0.18,
        )
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
                marker={
                    "size": 10,
                    "color": _ACCENT,
                    "line": {"width": 0.6, "color": _MARKER_LINE},
                },
                line={"width": 1.6, "color": "rgba(86, 180, 233, 0.45)"},
                text=hover,
                hovertemplate="%{text}<br>rank=%{x}<br>strength=%{y:,.0f}<extra></extra>",
            )
        ]
    )
    fig.update_layout(
        **_dark_layout(
            title={
                "text": (
                    "Node strength distribution — dense trade graph "
                    "(no power-law fit; scale-free framing does not apply)"
                ),
                "x": 0.01,
                "xanchor": "left",
                "font": {"size": _FS_TITLE, "color": _INK},
            },
            xaxis=_axis_dark(title={"text": "Rank (1 = largest)"}, fixedrange=False),
            yaxis=_axis_dark(title={"text": label}, type="log", fixedrange=False),
            margin={"l": 80, "r": 30, "t": 80, "b": 110},
            height=540,
            width=960,
            showlegend=False,
            annotations=[
                _footnote(
                    "Near-complete bilateral coverage ⇒ high density; "
                    "use the disparity-filter backbone for structure.",
                    y=-0.26,
                )
            ],
        )
    )
    return fig


# Okabe–Ito qualitative palette (colour-blind safe) for community fills, cycled.
_COMMUNITY_COLORS: tuple[str, ...] = (
    "#56B4E9",  # sky blue
    "#E69F00",  # orange
    "#009E73",  # bluish green
    "#F0E442",  # yellow
    "#CC79A7",  # reddish purple
    "#0072B2",  # blue
    "#D55E00",  # vermillion
    "#999999",  # grey
)


def plot_community_map(
    node_meta: pd.DataFrame,
    partition: dict[str, int],
    edgelist: pd.DataFrame | None = None,
    title: str | None = None,
) -> go.Figure:
    """Geographic map of trade communities: nodes coloured by Louvain community.

    Nodes sit at lon/lat, coloured by community and sized by export strength. When
    ``edgelist`` is supplied (e.g. the backbone) its edges are drawn faintly so the
    bloc structure is visible against geography. Kaleido-safe Cartesian axes.

    Args:
        node_meta: Nodes with ``iso3``, ``lat``, ``lon``; optional ``name``,
            ``out_strength``.
        partition: Mapping ISO3 → community id.
        edgelist: Optional edges (``exporter_iso3``, ``importer_iso3``, ``value_kusd``)
            drawn as faint background lines.
        title: Optional figure title.

    Returns:
        Plotly figure ready for display or :func:`save_fig`.
    """
    required_node = {"iso3", "lat", "lon"}
    missing_node = required_node - set(node_meta.columns)
    if missing_node:
        raise ValueError(f"node_meta missing columns: {sorted(missing_node)}")

    meta = node_meta.copy().reset_index(drop=True)
    meta["iso3"] = meta["iso3"].astype(str)
    meta["community"] = [int(partition.get(str(i), -1)) for i in meta["iso3"]]
    coords = {
        str(iso3): (float(lat), float(lon))
        for iso3, lat, lon in meta[["iso3", "lat", "lon"]].itertuples(index=False, name=None)
    }

    if "out_strength" in meta.columns:
        s_vals = meta["out_strength"].astype(float).to_numpy()
    else:
        s_vals = pd.Series([1.0] * len(meta)).to_numpy()
    s_max = float(s_vals.max()) if len(s_vals) else 1.0
    sizes = (9.0 + 20.0 * (s_vals / s_max) ** 0.5).tolist()

    fig = go.Figure()

    if edgelist is not None and len(edgelist):
        max_val = float(edgelist["value_kusd"].to_numpy().max())
        for exporter, importer, value in edgelist[
            ["exporter_iso3", "importer_iso3", "value_kusd"]
        ].itertuples(index=False, name=None):
            exp, imp = str(exporter), str(importer)
            if exp not in coords or imp not in coords:
                continue
            lat0, lon0 = coords[exp]
            lat1, lon1 = coords[imp]
            share = float(value) / max_val
            fig.add_trace(
                go.Scatter(
                    x=[lon0, lon1, None],
                    y=[lat0, lat1, None],
                    mode="lines",
                    line={"width": 0.3 + 1.4 * (share**0.7), "color": _EDGE.format(alpha=0.22)},
                    hoverinfo="skip",
                    showlegend=False,
                )
            )

    names = (
        meta["name"].astype(str).tolist()
        if "name" in meta.columns
        else meta["iso3"].astype(str).tolist()
    )
    hover = [f"{n} ({i})" for n, i in zip(names, meta["iso3"].astype(str), strict=True)]

    for comm_id in sorted({int(c) for c in meta["community"] if int(c) >= 0}):
        frame = meta.loc[meta["community"] == comm_id]
        if frame.empty:
            continue
        sub_idx = frame.index.to_numpy()
        color = _COMMUNITY_COLORS[comm_id % len(_COMMUNITY_COLORS)]
        fig.add_trace(
            go.Scatter(
                x=frame["lon"].astype(float).tolist(),
                y=frame["lat"].astype(float).tolist(),
                mode="markers",
                name=f"Community {comm_id}",
                marker={
                    "size": [sizes[int(i)] for i in sub_idx],
                    "color": color,
                    "line": {"width": 0.7, "color": _MARKER_LINE},
                    "opacity": 0.95,
                },
                customdata=[hover[int(i)] for i in sub_idx],
                hovertemplate="%{customdata}<extra></extra>",
            )
        )

    lon_min = float(meta["lon"].to_numpy(dtype=float).min())
    lon_max = float(meta["lon"].to_numpy(dtype=float).max())
    lat_min = float(meta["lat"].to_numpy(dtype=float).min())
    lat_max = float(meta["lat"].to_numpy(dtype=float).max())
    x_range = (lon_min - 10.0, lon_max + 10.0)
    y_range = (lat_min - 4.0, lat_max + 6.0)

    fig_w, fig_h = 1120, 560
    margin = {"l": 70, "r": 30, "t": 70, "b": 90}

    labels = [
        {"x": float(lon), "y": float(lat), "text": iso}
        for iso, lat, lon in meta[["iso3", "lat", "lon"]].itertuples(index=False, name=None)
    ]
    obstacles = tuple(
        (float(lon), float(lat))
        for lon, lat in meta[["lon", "lat"]].itertuples(index=False, name=None)
    )
    annotations = _place_labels(
        labels,
        x_range=x_range,
        y_range=y_range,
        fig_w=fig_w,
        fig_h=fig_h,
        margin=margin,
        obstacles=obstacles,
    )
    annotations.append(
        _footnote(
            "Node colour = Louvain community · size ∝ export strength · "
            "faint lines = backbone edges",
            y=-0.18,
        )
    )

    fig.update_layout(
        **_dark_layout(
            title={
                "text": title or "Trade communities (Louvain)",
                "x": 0.02,
                "xanchor": "left",
                "font": {"size": _FS_TITLE, "color": _INK},
            },
            xaxis=_axis_dark(title={"text": "Longitude"}, range=list(x_range)),
            yaxis=_axis_dark(title={"text": "Latitude"}, range=list(y_range)),
            margin=margin,
            height=fig_h,
            width=fig_w,
            showlegend=True,
            annotations=annotations,
        )
    )
    return fig


# Injected once into the generated HTML: overlay panel / legend / control styling.
_PYVIS_UI_CSS = """
<style>
#eutn-panel, #eutn-legend, #eutn-controls {
  position: fixed; z-index: 1000;
  background: rgba(18,20,26,0.88); color: #e8eaed;
  border: 1px solid rgba(255,255,255,0.14); border-radius: 8px;
  font-family: "IBM Plex Sans", Arial, sans-serif; font-size: 13px; line-height: 1.45;
  box-shadow: 0 4px 18px rgba(0,0,0,0.45);
}
#eutn-panel { top: 14px; left: 14px; max-width: 340px; padding: 12px 14px; }
#eutn-panel h1 { font-size: 16px; margin: 0 0 4px; color: #ffffff; }
#eutn-panel .sub { color: #b4b9c2; font-size: 12px; margin-bottom: 8px; }
#eutn-panel .desc { color: #d7dae0; }
#eutn-panel .tips { color: #b4b9c2; font-size: 12px; margin-top: 8px;
  border-top: 1px solid rgba(255,255,255,0.1); padding-top: 6px; }
#eutn-legend { bottom: 16px; left: 14px; padding: 10px 12px; max-width: 320px; }
#eutn-legend .row { display: flex; align-items: center; margin: 3px 0; }
#eutn-legend .swatch { width: 13px; height: 13px; border-radius: 50%; margin-right: 8px;
  border: 1px solid rgba(255,255,255,0.25); flex: 0 0 auto; }
#eutn-legend .bar { width: 26px; border-top: 3px solid rgba(86,180,233,0.75);
  margin-right: 8px; flex: 0 0 auto; }
#eutn-legend .sizedot { width: 14px; height: 14px; border-radius: 50%;
  background: #b4b9c2; margin-right: 8px; flex: 0 0 auto; }
#eutn-legend hr { border: none; border-top: 1px solid rgba(255,255,255,0.12); margin: 8px 0; }
#eutn-legend .cap { color: #b4b9c2; font-size: 11px; text-transform: uppercase;
  letter-spacing: .04em; margin-bottom: 4px; }
#eutn-controls { top: 14px; right: 14px; padding: 8px; display: flex;
  flex-direction: column; gap: 6px; }
#eutn-controls button { background: #1a1d26; color: #e8eaed;
  border: 1px solid rgba(255,255,255,0.18); border-radius: 6px; padding: 6px 10px;
  font-size: 12px; cursor: pointer; font-family: inherit; text-align: left; }
#eutn-controls button:hover { background: #2a2f3a; border-color: #56B4E9; }
</style>
"""

# Injected before `new vis.Network(...)`: restore HTML rendering in node tooltips
# (modern vis-network shows the `title` string as plain text for XSS safety, so the
# `<br>` tags in our tooltips would otherwise render literally).
_PYVIS_TOOLTIP_FIX = """
function htmlTitle(html) {
  var container = document.createElement("div");
  container.style.whiteSpace = "normal";
  container.style.maxWidth = "260px";
  container.innerHTML = html;
  return container;
}
nodes.forEach(function (n) {
  if (typeof n.title === "string") {
    nodes.update({ id: n.id, title: htmlTitle(n.title) });
  }
});
"""

# Injected before `</body>`: wire up the control buttons once the network exists.
_PYVIS_UI_SCRIPT = """
<script type="text/javascript">
(function () {
  function ready() {
    if (typeof network === "undefined" || !network) { setTimeout(ready, 120); return; }
    network.setOptions({ interaction: { hover: true, tooltipDelay: 120, keyboard: true,
      multiselect: true } });
    var physicsOn = true;
    var freezeBtn = document.getElementById("eutn-freeze");
    freezeBtn.onclick = function () {
      physicsOn = !physicsOn;
      network.setOptions({ physics: { enabled: physicsOn } });
      freezeBtn.textContent = physicsOn ? "Freeze layout" : "Resume layout";
    };
    document.getElementById("eutn-fit").onclick = function () {
      network.fit({ animation: true });
    };
    var labelsOn = true, saved = {};
    if (typeof nodes !== "undefined") { nodes.forEach(function (n) { saved[n.id] = n.label; }); }
    var labelsBtn = document.getElementById("eutn-labels");
    labelsBtn.onclick = function () {
      labelsOn = !labelsOn;
      var upd = [];
      nodes.forEach(function (n) { upd.push({ id: n.id, label: labelsOn ? saved[n.id] : "" }); });
      nodes.update(upd);
      labelsBtn.textContent = labelsOn ? "Hide labels" : "Show labels";
    };
  }
  if (document.readyState === "complete") { ready(); }
  else { window.addEventListener("load", ready); }
})();
</script>
"""


def _pyvis_overlay_html(
    partition: dict[str, int],
    title: str,
    subtitle: str,
    description: str,
    community_labels: dict[int, str] | None,
) -> str:
    """Build the fixed-position overlay (header, controls, legend) for the PyVis page."""
    counts: dict[int, int] = {}
    for comm in partition.values():
        counts[int(comm)] = counts.get(int(comm), 0) + 1

    rows: list[str] = []
    for cid in sorted(counts):
        color = _COMMUNITY_COLORS[cid % len(_COMMUNITY_COLORS)]
        if community_labels and cid in community_labels:
            label = community_labels[cid]
        else:
            label = f"Community {cid} · {counts[cid]} economies"
        rows.append(
            f'<div class="row"><span class="swatch" style="background:{color}"></span>{label}</div>'
        )
    legend_rows = "\n      ".join(rows)

    return f"""
<div id="eutn-panel">
  <h1>{title}</h1>
  <div class="sub">{subtitle}</div>
  <div class="desc">{description}</div>
  <div class="tips">Hover a node for country details &middot; drag nodes to rearrange &middot;
    scroll to zoom &middot; use the buttons (top-right) to freeze the layout or refit.</div>
</div>
<div id="eutn-controls">
  <button id="eutn-freeze">Freeze layout</button>
  <button id="eutn-fit">Fit to screen</button>
  <button id="eutn-labels">Hide labels</button>
</div>
<div id="eutn-legend">
  <div class="cap">Trade communities</div>
  {legend_rows}
  <hr>
  <div class="cap">Encoding</div>
  <div class="row"><span class="sizedot"></span>Node size &prop; total trade strength</div>
  <div class="row"><span class="bar"></span>Edge width &prop; bilateral trade value</div>
</div>
"""


def plot_network_pyvis(
    undirected: nx.Graph,
    partition: dict[str, int],
    out_html: Path,
    *,
    title: str = "European trade communities",
    subtitle: str = "Weighted Louvain community detection",
    description: str = (
        "An interactive view of the European merchandise-trade network (CEPII BACI). "
        "Each node is an economy; colour marks its detected trade community, size scales "
        "with total trade strength, and edges are bilateral trade flows."
    ),
    community_labels: dict[int, str] | None = None,
    label_size: int = 60,
) -> None:
    """Write an interactive PyVis network: node size ∝ strength, colour = community.

    Node size scales with weighted degree (total trade strength); node colour encodes
    the Louvain community. Edge thickness scales with the summed bilateral trade value.
    The generated HTML is post-processed to (a) restore HTML rendering in the hover
    tooltips, and (b) add a fixed overlay with a title/description, a colour legend, and
    control buttons (freeze layout, fit to screen, toggle labels). Resources are inlined,
    so the file is fully self-contained.

    Args:
        undirected: Undirected weighted graph (edge ``weight`` = summed trade value);
            nodes may carry ``name`` / ``grp`` attributes for hover text.
        partition: Mapping ISO3 → community id (see :func:`communities.detect_communities`).
        out_html: Destination ``.html`` path (parent dirs are created).
        title: Heading shown in the overlay panel.
        subtitle: Secondary line under the heading (e.g. ``K`` and modularity).
        description: Short paragraph explaining what the visualisation shows.
        community_labels: Optional mapping community id → legend label. Defaults to a
            generic ``"Community {id} · {n} economies"`` label.
        label_size: Node label font size in px (independent of zoom). Larger values keep
            the ISO3 labels readable without zooming in.
    """
    from pyvis.network import Network

    strengths = {n: float(d) for n, d in undirected.degree(weight="weight")}
    s_max = max(strengths.values()) if strengths else 1.0
    weights = [float(d.get("weight", 0.0)) for _, _, d in undirected.edges(data=True)]
    w_max = max(weights) if weights else 1.0

    net = Network(
        height="100vh",
        width="100%",
        bgcolor=_PAPER,
        font_color=_INK,  # type: ignore[arg-type]  # pyvis stub mistypes this as bool
        directed=False,
        cdn_resources="in_line",
        notebook=False,
    )
    net.barnes_hut(gravity=-12000, central_gravity=0.4, spring_length=120)

    for node in undirected.nodes:
        iso3 = str(node)
        attrs = undirected.nodes[node]
        comm = int(partition.get(iso3, -1))
        color = _COMMUNITY_COLORS[comm % len(_COMMUNITY_COLORS)] if comm >= 0 else _MUTED
        size = 10.0 + 40.0 * (strengths.get(node, 0.0) / s_max) ** 0.5
        name = str(attrs.get("name", iso3))
        grp = str(attrs.get("grp", ""))
        title_html = (
            f"<b>{name}</b> ({iso3})<br>Community {comm}"
            f"{f' &middot; {grp}' if grp else ''}"
            f"<br>Trade strength: {strengths.get(node, 0.0):,.0f} kUSD"
        )
        net.add_node(
            iso3,
            label=iso3,
            title=title_html,
            size=size,
            color=color,
            borderWidth=1,
        )

    for u, v, data in undirected.edges(data=True):
        w = float(data.get("weight", 0.0))
        net.add_edge(str(u), str(v), value=w, width=0.4 + 4.0 * (w / w_max) ** 0.6)

    out_html = Path(out_html)
    out_html.parent.mkdir(parents=True, exist_ok=True)
    net.write_html(str(out_html), notebook=False, open_browser=False)

    html = out_html.read_text(encoding="utf-8")
    # pyvis fixes each node's font to just the colour, ignoring any font size passed to
    # add_node. Enlarge the ISO3 labels (with a dark outline for contrast) by rewriting
    # that font object directly so labels are readable without zooming in.
    node_font_src = f'"font": {{"color": "{_INK}"}}'
    node_font_dst = (
        f'"font": {{"color": "{_INK}", "size": {label_size}, '
        f'"face": "IBM Plex Sans, Arial, sans-serif", '
        f'"strokeWidth": 4, "strokeColor": "{_PAPER}"}}'
    )
    html = html.replace(node_font_src, node_font_dst)
    net_anchor = "network = new vis.Network(container, data, options);"
    if net_anchor in html:
        html = html.replace(net_anchor, _PYVIS_TOOLTIP_FIX + "\n                  " + net_anchor, 1)
    overlay = _pyvis_overlay_html(partition, title, subtitle, description, community_labels)
    html = html.replace("</body>", _PYVIS_UI_CSS + overlay + _PYVIS_UI_SCRIPT + "\n    </body>", 1)
    out_html.write_text(html, encoding="utf-8")


# Removal strategies keep a fixed colour so figures are comparable across notebooks.
_RESILIENCE_COLORS: dict[str, str] = {
    "random": "#999999",  # grey
    "targeted (out-strength)": "#E69F00",  # orange
    "targeted (betweenness)": "#CC79A7",  # reddish purple
}


def _rgba(hex_color: str, alpha: float) -> str:
    """Convert ``#rrggbb`` to an ``rgba(...)`` string with the given alpha."""
    raw = hex_color.lstrip("#")
    r, g, b = (int(raw[i : i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{alpha:.3f})"


def plot_resilience(
    curves: pd.DataFrame,
    title: str | None = None,
    lcc_level: float = 0.5,
) -> go.Figure:
    """Targeted vs random removal curves (LCC fraction and trade retained).

    Two panels sharing the x axis (fraction of economies removed): the largest
    weakly-connected component as a share of the *surviving* nodes, and the share of the
    original trade value still carried inside that component. Where a strategy reports a
    spread across seeded runs (``*_sd`` columns), a ±1 sd band is shaded.

    Args:
        curves: Long-form removal curves from
            :func:`resilience.run_random_vs_targeted` — needs ``strategy``,
            ``fraction_removed``, ``lcc_fraction``, ``trade_value_retained``; optional
            ``lcc_fraction_sd`` / ``trade_value_retained_sd``.
        title: Optional figure title.
        lcc_level: Fragmentation level marked with a dotted reference line.

    Returns:
        Plotly figure ready for display or :func:`save_fig`.
    """
    required = {"strategy", "fraction_removed", "lcc_fraction", "trade_value_retained"}
    missing = required - set(curves.columns)
    if missing:
        raise ValueError(f"curves missing columns: {sorted(missing)}")

    fig_w, fig_h = 1180, 540
    margin = {"l": 78, "r": 30, "t": 96, "b": 126}
    # No subplot titles: the y-axis labels already name each panel, and dropping them
    # leaves the top strip free for the legend.
    fig = make_subplots(rows=1, cols=2, horizontal_spacing=0.10)

    fig.add_trace(
        go.Scatter(
            x=[0.0, 1.0],
            y=[lcc_level, lcc_level],
            mode="lines",
            line={"dash": "dot", "width": 1.2, "color": _MUTED},
            showlegend=False,
            hoverinfo="skip",
        ),
        row=1,
        col=1,
    )

    panels = (
        ("lcc_fraction", "lcc_fraction_sd"),
        ("trade_value_retained", "trade_value_retained_sd"),
    )
    strategies = list(dict.fromkeys(curves["strategy"].astype(str)))
    for idx, strategy in enumerate(strategies):
        frame = curves.loc[curves["strategy"].astype(str) == strategy].sort_values(
            "fraction_removed"
        )
        color = _RESILIENCE_COLORS.get(strategy, _COMMUNITY_COLORS[idx % len(_COMMUNITY_COLORS)])
        x = frame["fraction_removed"].astype(float).to_numpy()

        for col, (value_col, sd_col) in enumerate(panels, start=1):
            y = frame[value_col].astype(float).to_numpy()
            if sd_col in frame.columns:
                sd = frame[sd_col].astype(float).fillna(0.0).to_numpy()
                if float(sd.max()) > 0.0:
                    for bound, fill in (
                        ((y + sd).clip(max=1.0), None),
                        ((y - sd).clip(min=0.0), "tonexty"),
                    ):
                        fig.add_trace(
                            go.Scatter(
                                x=x.tolist(),
                                y=bound.tolist(),
                                mode="lines",
                                line={"width": 0.0, "color": "rgba(0,0,0,0)"},
                                fill=fill,
                                fillcolor=_rgba(color, 0.11),
                                legendgroup=strategy,
                                showlegend=False,
                                hoverinfo="skip",
                            ),
                            row=1,
                            col=col,
                        )
            fig.add_trace(
                go.Scatter(
                    x=x.tolist(),
                    y=y.tolist(),
                    mode="lines+markers",
                    name=strategy,
                    legendgroup=strategy,
                    showlegend=bool(col == 1),
                    line={"width": 2.2, "color": color},
                    marker={"size": 4, "color": color},
                    hovertemplate=(
                        f"{strategy}<br>removed=%{{x:.0%}}<br>{value_col}=%{{y:.1%}}<extra></extra>"
                    ),
                ),
                row=1,
                col=col,
            )

    for col, label in enumerate(
        (
            "Largest connected component (share of survivors)",
            "Trade value retained inside it (share of original)",
        ),
        start=1,
    ):
        # Both axes are percentages starting at zero, so their "0%" labels would collide
        # in the corner. Only the y axis prints it; it reads as the origin for both.
        fig.update_xaxes(
            **_axis_dark(
                title_text="Fraction of economies removed",
                range=[0.0, 1.0],
                tickformat=".0%",
                tickvals=[0.2, 0.4, 0.6, 0.8, 1.0],
            ),
            row=1,
            col=col,
        )
        fig.update_yaxes(
            **_axis_dark(
                title_text=label,
                range=[0.0, 1.05],
                tickformat=".0%",
                tickvals=[0.0, 0.2, 0.4, 0.6, 0.8, 1.0],
            ),
            row=1,
            col=col,
        )

    fig.update_layout(
        **_dark_layout(
            title={
                "text": title or "Network resilience — targeted attack vs random failure",
                "x": 0.01,
                "xanchor": "left",
                "font": {"size": _FS_TITLE, "color": _INK},
            },
            height=fig_h,
            width=fig_w,
            margin=margin,
            showlegend=True,
        )
    )
    fig.add_annotation(
        x=0.02,
        y=lcc_level,
        xref="x",
        yref="y",
        text=f"fragmentation level ({lcc_level:.0%})",
        showarrow=False,
        xanchor="left",
        yanchor="bottom",
        font={"size": _FS_FOOT, "color": _MUTED},
    )
    fig.add_annotation(
        **_footnote(
            "Economies removed one at a time · targeted rankings fixed on the intact network · "
            "random = mean of seeded runs (shaded ±1 sd)<br>"
            "The component share is measured against surviving economies, so it rebounds once "
            "only a handful of isolated economies are left.",
            y=-0.30,
        )
    )
    return fig


# Energy figure: sky blue = all merchandise, orange = energy, purple = focus economy.
_ENERGY_FOCUS = "#CC79A7"  # reddish purple

# Pinned energy-comparison geometry (the label solver needs the rendered pixel sizes).
_EN_W = 1240
_EN_H = 560
_EN_MARGIN = {"l": 78, "r": 40, "t": 132, "b": 132}


def plot_energy_comparison(
    total_shares: pd.DataFrame,
    energy_shares: pd.DataFrame,
    focus_iso3: str = "AUT",
    top_k: int = 3,
    labels: tuple[str, str] = ("All merchandise", "Energy (HS-27)"),
    n_labelled: int = 5,
    title: str | None = None,
) -> go.Figure:
    """Energy subnetwork vs total trade: export concentration and per-economy specialisation.

    Left: cumulative share of network exports by exporter rank, one curve per network —
    the steeper curve is the more concentrated market, with the ``top_k`` point marked.
    Right: each economy's share of energy exports against its share of merchandise exports
    (log-log). The diagonal is "energy share = merchandise share", so economies above it are
    energy-specialised; ``focus_iso3`` is highlighted.

    Args:
        total_shares: Output of ``energy.trade_shares`` for the all-merchandise graph.
        energy_shares: Output of ``energy.trade_shares`` for the energy subgraph.
        focus_iso3: Economy to highlight in the scatter (Austria by default).
        top_k: Concentration marker on the cumulative curve.
        labels: Names of the two networks, in the order ``(total, energy)``.
        n_labelled: Number of leading exporters labelled per network in the scatter.
        title: Optional figure title.

    Returns:
        Plotly figure ready for display or :func:`save_fig`.
    """
    required = {"iso3", "export_share"}
    for name, frame in zip(labels, (total_shares, energy_shares), strict=True):
        missing = required - set(frame.columns)
        if missing:
            raise ValueError(f"{name} shares missing columns: {sorted(missing)}")

    total_label, energy_label = labels
    fig = make_subplots(
        rows=1,
        cols=2,
        horizontal_spacing=0.10,
        subplot_titles=(
            "Export concentration (cumulative share by rank)",
            "Energy specialisation (share of exports, log scale)",
        ),
    )
    # Restyle the make_subplots panel titles before any other annotation is added.
    fig.update_annotations(font={"color": _INK, "size": _FS_SUBTITLE})

    # --- Panel 1: cumulative concentration curves ---------------------------------
    top_k_shares: dict[str, float] = {}
    for label, frame, color in (
        (total_label, total_shares, _ACCENT),
        (energy_label, energy_shares, _PARTNER),
    ):
        ranked = sorted((float(share) for share in frame["export_share"]), reverse=True)
        cumulative: list[float] = []
        running = 0.0
        for share in ranked:
            running += share
            cumulative.append(running)
        top_k_shares[label] = cumulative[min(top_k, len(cumulative)) - 1]
        fig.add_trace(
            go.Scatter(
                x=list(range(1, len(cumulative) + 1)),
                y=cumulative,
                mode="lines+markers",
                name=label,
                legendgroup=label,
                line={"width": 2.4, "color": color},
                marker={"size": 5, "color": color},
                hovertemplate=f"{label}<br>top %{{x}} exporters = %{{y:.1%}}<extra></extra>",
            ),
            row=1,
            col=1,
        )

    fig.add_trace(
        go.Scatter(
            x=[top_k, top_k],
            y=[0.0, max(top_k_shares.values())],
            mode="lines",
            line={"dash": "dot", "width": 1.2, "color": _MUTED},
            showlegend=False,
            hoverinfo="skip",
        ),
        row=1,
        col=1,
    )
    fig.add_annotation(
        x=0.95,
        y=0.06,
        xref="x domain",
        yref="y domain",
        text=(
            f"Top {top_k} exporters carry <b>{top_k_shares[energy_label]:.0%}</b> of energy "
            f"exports<br>vs {top_k_shares[total_label]:.0%} of all merchandise exports"
        ),
        showarrow=False,
        xanchor="right",
        yanchor="bottom",
        font={"size": _FS_LABEL, "color": _INK},
        bgcolor="rgba(18,20,26,0.78)",
        bordercolor="rgba(255,255,255,0.16)",
        borderwidth=1,
        borderpad=3,
    )

    # --- Panel 2: energy share vs merchandise share -------------------------------
    merged = total_shares[["iso3", "export_share"]].merge(
        energy_shares[["iso3", "export_share"]],
        on="iso3",
        how="inner",
        suffixes=("_total", "_energy"),
    )
    merged = merged.loc[
        (merged["export_share_total"] > 0.0) & (merged["export_share_energy"] > 0.0)
    ].reset_index(drop=True)
    merged["specialised"] = merged["export_share_energy"] > merged["export_share_total"]

    lo = float(min(merged["export_share_total"].min(), merged["export_share_energy"].min()))
    hi = float(max(merged["export_share_total"].max(), merged["export_share_energy"].max()))
    log_lo, log_hi = math.log10(lo) - 0.4, math.log10(hi) + 0.55

    fig.add_trace(
        go.Scatter(
            x=[10**log_lo, 10**log_hi],
            y=[10**log_lo, 10**log_hi],
            mode="lines",
            line={"dash": "dot", "width": 1.2, "color": _MUTED},
            showlegend=False,
            hoverinfo="skip",
        ),
        row=1,
        col=2,
    )

    focus_mask = merged["iso3"].astype(str) == focus_iso3
    others = ~focus_mask
    groups = (
        (
            "Energy-specialised (above the line)",
            merged.loc[merged["specialised"] & others],
            _PARTNER,
        ),
        ("Energy-light (below the line)", merged.loc[~merged["specialised"] & others], _ACCENT),
        (focus_iso3, merged.loc[focus_mask], _ENERGY_FOCUS),
    )
    for name, frame, color in groups:
        if frame.empty:
            continue
        fig.add_trace(
            go.Scatter(
                x=frame["export_share_total"].astype(float).tolist(),
                y=frame["export_share_energy"].astype(float).tolist(),
                mode="markers",
                name=name,
                marker={
                    "size": 15 if name == focus_iso3 else 10,
                    "color": color,
                    "line": {"width": 0.8, "color": _MARKER_LINE},
                    "symbol": "diamond" if name == focus_iso3 else "circle",
                },
                text=frame["iso3"].astype(str).tolist(),
                hovertemplate=(
                    "%{text}<br>merchandise = %{x:.2%}<br>energy = %{y:.2%}<extra></extra>"
                ),
            ),
            row=1,
            col=2,
        )

    fig.update_xaxes(
        **_axis_dark(title_text="Exporter rank (1 = largest)", range=[0.5, len(merged) + 0.5]),
        row=1,
        col=1,
    )
    fig.update_yaxes(
        **_axis_dark(
            title_text="Cumulative share of network exports",
            range=[0.0, 1.05],
            tickformat=".0%",
        ),
        row=1,
        col=1,
    )
    share_ticks = [1e-4, 1e-3, 1e-2, 1e-1]
    share_text = ["0.01%", "0.1%", "1%", "10%"]
    fig.update_xaxes(
        **_axis_dark(
            title_text=f"Share of {total_label.lower()} exports",
            type="log",
            range=[log_lo, log_hi],
            tickvals=share_ticks,
            ticktext=share_text,
        ),
        row=1,
        col=2,
    )
    fig.update_yaxes(
        **_axis_dark(
            title_text="Share of energy exports",
            type="log",
            range=[log_lo, log_hi],
            tickvals=share_ticks,
            ticktext=share_text,
        ),
        row=1,
        col=2,
    )

    fig.update_layout(
        **_dark_layout(
            title={
                "text": title
                or "Energy (HS-27) exports are far more concentrated than merchandise trade",
                "x": 0.01,
                "xanchor": "left",
                "font": {"size": _FS_TITLE, "color": _INK},
            },
            height=_EN_H,
            width=_EN_W,
            margin=_EN_MARGIN,
            legend={
                "orientation": "h",
                "yanchor": "bottom",
                "y": 1.10,
                "xanchor": "right",
                "x": 1.0,
                "bgcolor": "rgba(18,20,26,0.55)",
                "bordercolor": "rgba(255,255,255,0.12)",
                "borderwidth": 1,
                "font": {"color": _INK, "size": _FS_LEGEND},
            },
        )
    )
    # Label the focus economy first (it gets the best free slot), then the leading
    # exporters of each network.
    hubs: list[str] = [focus_iso3]
    for frame in (energy_shares, total_shares):
        leaders = frame.sort_values("export_share", ascending=False)["iso3"].astype(str)
        hubs.extend(iso for iso in leaders.head(n_labelled) if iso not in hubs)

    by_iso = merged.set_index(merged["iso3"].astype(str))
    points = [
        {
            "x": math.log10(float(by_iso.loc[iso, "export_share_total"])),
            "y": math.log10(float(by_iso.loc[iso, "export_share_energy"])),
            "text": iso,
        }
        for iso in hubs
        if iso in by_iso.index
    ]
    obstacles = tuple(
        (math.log10(float(x)), math.log10(float(y)))
        for x, y in merged[["export_share_total", "export_share_energy"]].itertuples(
            index=False, name=None
        )
    )
    for ann in _place_labels(
        points,
        x_range=(log_lo, log_hi),
        y_range=(log_lo, log_hi),
        fig_w=_EN_W,
        fig_h=_EN_H,
        margin=_EN_MARGIN,
        x_domain=(0.55, 1.0),
        y_domain=(0.0, 1.0),
        xref="x2",
        yref="y2",
        obstacles=obstacles,
        radii=(30.0, 46.0, 66.0, 92.0, 120.0),
    ):
        fig.add_annotation(**ann)

    fig.add_annotation(
        **_footnote(
            "Exports valued in thousand USD (CEPII BACI) · shares are of trade "
            "<i>within</i> the 35-economy node set<br>"
            "Dotted diagonal: energy share = merchandise share. Above it, an economy is "
            "more important in energy than its overall trade weight implies.",
            y=-0.28,
        )
    )
    return fig


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
