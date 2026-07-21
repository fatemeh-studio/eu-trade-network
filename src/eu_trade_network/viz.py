"""Plotly / PyVis / Matplotlib figures. Headline PNGs go to figures/headline/."""

from pathlib import Path

import networkx as nx
import pandas as pd
import plotly.graph_objects as go

from . import config


def plot_flow_map(edgelist: pd.DataFrame, node_meta: pd.DataFrame, top_n: int = 150) -> go.Figure:
    """Scattergeo hero map: nodes at lat/lon, the ``top_n`` edges by value as lines."""
    raise NotImplementedError("TODO: implement in Cursor Prompt P2")


def plot_degree_distribution(strength: pd.DataFrame) -> go.Figure:
    """Strength distribution (this network is dense — do NOT force a power-law fit)."""
    raise NotImplementedError("TODO: implement in Cursor Prompt P3")


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
    """Write a figure to ``headline_dir`` (committed) or ``qa_dir`` (gitignored) as PNG."""
    raise NotImplementedError("TODO: implement in Cursor Prompt P2")
