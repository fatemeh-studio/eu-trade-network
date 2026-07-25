"""Unit tests for the energy (HS-27) subnetwork comparison, on synthetic data."""

from __future__ import annotations

import networkx as nx
import pandas as pd
import pytest

from eu_trade_network.energy import (
    HS27_HEADINGS,
    comparison_table,
    concentration,
    country_position,
    heading_composition,
    sourcing_summary,
    trade_shares,
)


@pytest.fixture
def total_graph() -> nx.DiGraph:
    """Four economies; A exports 80% of the network's value, C and D tie on 5%."""
    g = nx.DiGraph()
    for u, v, w in (
        ("A", "B", 60.0),
        ("A", "C", 20.0),
        ("B", "A", 10.0),
        ("C", "A", 5.0),
        ("D", "A", 5.0),
    ):
        g.add_edge(u, v, weight=w)
    return g


@pytest.fixture
def energy_graph() -> nx.DiGraph:
    """Same node set, but D is the dominant exporter — an energy-specialised economy."""
    g = nx.DiGraph()
    for u, v, w in (
        ("D", "A", 70.0),
        ("D", "B", 10.0),
        ("A", "D", 15.0),
        ("B", "C", 5.0),
    ):
        g.add_edge(u, v, weight=w)
    g.add_node("C")
    return g


@pytest.fixture
def flows() -> pd.DataFrame:
    """Product-level energy flows shaped like :func:`energy.load_product_flows` output."""
    return pd.DataFrame(
        [
            ("AUT", "DEU", "2716", 100.0),
            ("DEU", "AUT", "2716", 50.0),
            ("DEU", "AUT", "2710", 150.0),
            ("RUS", "DEU", "2709", 200.0),
        ],
        columns=["exporter_iso3", "importer_iso3", "hs", "value_kusd"],
    )


def test_trade_shares_ranks_and_net_balance(total_graph: nx.DiGraph) -> None:
    shares = trade_shares(total_graph).set_index("iso3")

    assert shares["export_share"].sum() == pytest.approx(1.0)
    assert shares["import_share"].sum() == pytest.approx(1.0)
    assert shares.loc["A", "export_share"] == pytest.approx(0.8)
    assert shares.loc["A", "export_rank"] == 1
    # C and D both export 5% — a tie shares the better rank.
    assert shares.loc["C", "export_rank"] == 3
    assert shares.loc["D", "export_rank"] == 3
    # D imports nothing, so it is last by imports and a net exporter.
    assert shares.loc["D", "import_share"] == pytest.approx(0.0)
    assert shares.loc["D", "import_rank"] == 4
    assert shares.loc["D", "net_export_kusd"] == pytest.approx(5.0)
    assert shares.loc["A", "net_export_kusd"] == pytest.approx(60.0)


def test_trade_shares_rejects_a_valueless_graph() -> None:
    empty = nx.DiGraph()
    empty.add_edge("A", "B", weight=0.0)
    with pytest.raises(ValueError, match="no trade value"):
        trade_shares(empty)


def test_concentration(total_graph: nx.DiGraph, energy_graph: nx.DiGraph) -> None:
    total = concentration(trade_shares(total_graph), top_k=2)
    assert total["top_k_share"] == pytest.approx(0.9)
    assert total["hhi"] == pytest.approx(0.8**2 + 0.1**2 + 2 * 0.05**2)
    assert total["effective_exporters"] == pytest.approx(1.0 / total["hhi"])

    # The energy network puts 80% on one exporter, so it must be more concentrated.
    assert concentration(trade_shares(energy_graph), top_k=2)["hhi"] > total["hhi"]


def test_concentration_validates_input() -> None:
    with pytest.raises(ValueError, match="export_share"):
        concentration(pd.DataFrame({"iso3": ["A"]}))


def test_country_position(total_graph: nx.DiGraph) -> None:
    position = country_position(trade_shares(total_graph), "B")

    assert position["export_rank"] == 2
    assert position["import_rank"] == 1
    assert position["export_share"] == pytest.approx(0.1)
    assert position["net_export_kusd"] == pytest.approx(10.0 - 60.0)
    assert position["n_economies"] == 4

    with pytest.raises(KeyError, match="ZZZ"):
        country_position(trade_shares(total_graph), "ZZZ")


def test_comparison_table(total_graph: nx.DiGraph, energy_graph: nx.DiGraph) -> None:
    table = comparison_table(total_graph, energy_graph, focus_iso3="D", top_k=2).set_index("metric")

    assert list(table.columns) == ["All merchandise", "Energy (HS-27)"]
    assert table.loc["Trade value (bn USD)", "All merchandise"] == "0"  # 100k USD rounds to 0 bn
    assert table.loc["Share of merchandise value", "Energy (HS-27)"] == "100.0%"
    assert table.loc["Largest exporter", "All merchandise"] == "A (80.0%)"
    assert table.loc["Largest exporter", "Energy (HS-27)"] == "D (80.0%)"
    assert table.loc["Top 2 exporters", "Energy (HS-27)"] == "D, A"
    assert table.loc["Top 2 export share", "Energy (HS-27)"] == "95.0%"
    # The focus economy is marginal in merchandise trade but dominant in energy.
    assert table.loc["D export rank", "All merchandise"].startswith("3 of 4")
    assert table.loc["D export rank", "Energy (HS-27)"].startswith("1 of 4")


def test_sourcing_summary_splits_inside_and_outside_the_node_set() -> None:
    # DEU imports 100 of energy from RUS (inside) and 300 from a country outside the set,
    # plus 500 of non-energy from inside. AUT imports 50 of energy, all from inside.
    trade = pd.DataFrame(
        [
            ("RUS", "DEU", "270900", 100.0),
            ("SAU", "DEU", "270900", 300.0),
            ("CHN", "DEU", "850000", 500.0),
            ("DEU", "AUT", "271600", 50.0),
            ("DEU", "DEU", "270900", 999.0),  # self-trade is never part of the graph
        ],
        columns=["exporter_iso3", "importer_iso3", "k", "v"],
    )
    summary = sourcing_summary(
        trade, products=["27"], focus_iso3="AUT", countries=["DEU", "AUT", "RUS"]
    ).set_index(["scope", "importer"])

    all_trade = summary.loc[("All merchandise", "3-economy set")]
    assert all_trade["imports_world_kusd"] == pytest.approx(950.0)
    assert all_trade["imports_within_kusd"] == pytest.approx(150.0)

    energy_set = summary.loc[("Energy (HS-27)", "3-economy set")]
    assert energy_set["imports_world_kusd"] == pytest.approx(450.0)
    assert energy_set["imports_within_kusd"] == pytest.approx(150.0)
    assert energy_set["intra_share"] == pytest.approx(1 / 3)

    # Austria's energy imports are entirely intra-network here.
    assert summary.loc[("Energy (HS-27)", "AUT"), "intra_share"] == pytest.approx(1.0)


def test_heading_composition_whole_network(flows: pd.DataFrame) -> None:
    composition = heading_composition(flows).set_index("hs")

    assert composition["share"].sum() == pytest.approx(1.0)
    assert composition.loc["2709", "value_kusd"] == pytest.approx(200.0)
    assert composition.loc["2709", "share"] == pytest.approx(0.4)
    assert composition.loc["2716", "heading"] == HS27_HEADINGS["2716"]
    # Sorted by value, largest first.
    assert composition.index[0] == "2709"


def test_heading_composition_by_country_and_direction(flows: pd.DataFrame) -> None:
    imports = heading_composition(flows, iso3="AUT", direction="imports").set_index("hs")
    assert imports.loc["2710", "share"] == pytest.approx(0.75)
    assert imports.loc["2716", "share"] == pytest.approx(0.25)

    exports = heading_composition(flows, iso3="AUT", direction="exports")
    assert exports["hs"].tolist() == ["2716"]
    assert exports["share"].tolist() == pytest.approx([1.0])

    both = heading_composition(flows, iso3="AUT", direction="total").set_index("hs")
    assert both.loc["2716", "value_kusd"] == pytest.approx(150.0)
    assert both["share"].to_numpy() == pytest.approx([0.5, 0.5])


def test_heading_composition_rejects_unknown_direction(flows: pd.DataFrame) -> None:
    with pytest.raises(ValueError, match="unknown direction"):
        heading_composition(flows, iso3="AUT", direction="sideways")


def test_unknown_heading_falls_back_to_the_code() -> None:
    flows = pd.DataFrame(
        [("AUT", "DEU", "9999", 10.0)],
        columns=["exporter_iso3", "importer_iso3", "hs", "value_kusd"],
    )
    assert heading_composition(flows)["heading"].tolist() == ["9999"]
