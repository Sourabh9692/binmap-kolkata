import networkx as nx
import pytest
from shapely.geometry import Point, LineString
from binmap.geo import catchment, distance_to_bins


def graph():
    g = nx.MultiGraph()
    g.add_node(1, x=0, y=0)
    g.add_node(2, x=1000, y=0)
    g.add_edge(1, 2, geometry=LineString([(0, 0), (1000, 0)]), length=1000)
    return g


def test_anchor_in_long_edge_not_nearest_node():
    lines, offset = catchment(graph(), Point(500, 0), 100)
    assert sum(line.length for line, _ in lines) == pytest.approx(200)
    assert min(line.bounds[0] for line, _ in lines) == 400
    assert max(line.bounds[2] for line, _ in lines) == 600


def test_connector_cost_is_included():
    lines, offset = catchment(graph(), Point(500, 20), 100)
    assert offset == 20
    assert sum(line.length for line, _ in lines) == pytest.approx(160)


def test_unreasonable_snap_is_rejected():
    with pytest.raises(ValueError):
        catchment(graph(), Point(500, 60), 100)


def test_reversed_geometry_has_same_result():
    g = graph()
    g[1][2][0]["geometry"] = LineString([(1000, 0), (0, 0)])
    lines, _ = catchment(g, Point(500, 0), 100)
    assert sum(line.length for line, _ in lines) == pytest.approx(200)


def test_partially_reachable_branch():
    g = graph()
    g.add_node(3, x=1000, y=300)
    g.add_edge(2, 3, geometry=LineString([(1000, 0), (1000, 300)]), length=300)
    lines, _ = catchment(g, Point(900, 0), 150)
    assert sum(line.length for line, _ in lines) == pytest.approx(300)


def test_same_edge_distance_does_not_detour_to_nodes():
    assert distance_to_bins(graph(), Point(450, 0), [Point(500, 0)]) == pytest.approx(
        50
    )


def test_network_path_not_euclidean_shortcut():
    g = graph()
    g.add_node(3, x=1000, y=1000)
    g.add_node(4, x=0, y=1000)
    g.add_edge(2, 3, geometry=LineString([(1000, 0), (1000, 1000)]))
    g.add_edge(3, 4, geometry=LineString([(1000, 1000), (0, 1000)]))
    assert distance_to_bins(g, Point(0, 0), [Point(0, 1000)]) == pytest.approx(3000)


def test_no_bins_or_disconnected_bins_are_unknown():
    assert distance_to_bins(graph(), Point(450, 0), []) is None
    g = graph()
    g.add_node(3, x=0, y=1000)
    g.add_node(4, x=1000, y=1000)
    g.add_edge(3, 4, geometry=LineString([(0, 1000), (1000, 1000)]))
    assert distance_to_bins(g, Point(500, 0), [Point(500, 1000)]) is None
