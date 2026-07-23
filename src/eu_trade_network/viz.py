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
