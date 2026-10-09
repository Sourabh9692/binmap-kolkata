"""Metric, edge-based catchments. Inputs are projected, undirected walk graphs."""

import math
import networkx as nx
from shapely.geometry import Point, LineString
from shapely.ops import substring


def normalize_graph(graph):
    """Set metric lengths and orient geometry from u to v (independent of OSM direction)."""
    for u, v, k, data in graph.edges(keys=True, data=True):
        origin = Point(graph.nodes[u]["x"], graph.nodes[u]["y"])
        line = data.get(
            "geometry",
            LineString(
                [
                    (graph.nodes[u]["x"], graph.nodes[u]["y"]),
                    (graph.nodes[v]["x"], graph.nodes[v]["y"]),
                ]
            ),
        )
        if origin.distance(Point(line.coords[-1])) < origin.distance(
            Point(line.coords[0])
        ):
            line = LineString(list(line.coords)[::-1])
        data.update(geometry=line, length=line.length, oriented_u=u)
    return graph


def oriented(graph, u, v, data):
    line = data["geometry"]
    return line if data["oriented_u"] == u else LineString(list(line.coords)[::-1])


def catchment(graph, anchor, distance):
    """Include partial edges and anchor connector cost, including the interior of long edges."""
    if distance <= 0:
        raise ValueError("Distance must be positive")
    graph = normalize_graph(graph.copy())
    if not graph.edges:
        raise ValueError("Pedestrian graph is empty")
    u, v, k, d = min(
        graph.edges(keys=True, data=True),
        key=lambda e: e[3]["geometry"].distance(anchor),
    )
    line = oriented(graph, u, v, d)
    along = line.project(anchor)
    snap = line.interpolate(along)
    offset = anchor.distance(snap)
    if offset > 50:
        raise ValueError(
            f"Anchor is {offset:.1f} m from a walkable edge; manually verify its connection"
        )
    virtual = "binmap-anchor"
    graph.add_node(virtual, x=snap.x, y=snap.y)
    graph.remove_edge(u, v, k)
    for a, b, part in [
        (u, virtual, substring(line, 0, along)),
        (virtual, v, substring(line, along, line.length)),
    ]:
        if part.geom_type == "Point":
            part = LineString([part.coords[0], part.coords[0]])
        graph.add_edge(
            a,
            b,
            geometry=part,
            length=part.length,
            oriented_u=a,
            osmid=d.get("osmid"),
            name=d.get("name", "Unnamed lane"),
        )
    reachable = nx.single_source_dijkstra_path_length(
        graph, virtual, cutoff=distance - offset, weight="length"
    )
    lines = []
    for a, b, k, data in graph.edges(keys=True, data=True):
        geom = oriented(graph, a, b, data)
        length = geom.length
        if length < 0.01:
            continue
        left = min(length, max(0, distance - offset - reachable.get(a, math.inf)))
        right = min(length, max(0, distance - offset - reachable.get(b, math.inf)))
        intervals = []
        if left + right >= length:
            intervals = [(0, length)]
        else:
            if left > 0:
                intervals.append((0, left))
            if right > 0:
                intervals.append((length - right, length))
        for start, end in intervals:
            if end - start > 0.01:
                lines.append(
                    (
                        substring(geom, start, end),
                        {
                            "osmid": data.get("osmid"),
                            "name": data.get("name", "Unnamed lane"),
                        },
                    )
                )
    return lines, offset


def distance_to_bins(graph, point, bins, max_snap=30):
    """Exact along-edge shortest distance on this graph, including point-to-edge offsets.

    Suitable for small pilots. No eligible nearby bin yields None (unknown), never proof of absence.
    """
    if not bins:
        return None
    graph = normalize_graph(graph.copy())
    edges = list(graph.edges(keys=True, data=True))
    if not edges:
        return None
    target = min(edges, key=lambda e: e[3]["geometry"].distance(point))
    u, v, k, d = target
    line = oriented(graph, u, v, d)
    x = line.project(point)
    offset = line.distance(point)
    if offset > max_snap:
        return None
    distances_u = nx.single_source_dijkstra_path_length(graph, u, weight="length")
    distances_v = nx.single_source_dijkstra_path_length(graph, v, weight="length")
    best = math.inf
    for bin_point in bins:
        a, b, bk, bd = min(edges, key=lambda e: e[3]["geometry"].distance(bin_point))
        bline = oriented(graph, a, b, bd)
        y = bline.project(bin_point)
        gap = bline.distance(bin_point)
        if gap > max_snap:
            continue
        candidates = [
            x + distances_u.get(a, math.inf) + y,
            x + distances_u.get(b, math.inf) + bline.length - y,
            line.length - x + distances_v.get(a, math.inf) + y,
            line.length - x + distances_v.get(b, math.inf) + bline.length - y,
        ]
        if (u, v, k) == (a, b, bk):
            candidates.append(abs(x - y))
        best = min(best, offset + gap + min(candidates))
    return best if math.isfinite(best) else None
