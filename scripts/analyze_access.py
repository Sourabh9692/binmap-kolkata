#!/usr/bin/env python3
"""Sample walking distances to reviewed usable observations. Never infer absence from empty data."""

import argparse, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
import httpx, osmnx as ox
from pyproj import Transformer
from shapely.geometry import shape, mapping
from shapely.ops import transform
from binmap.geo import distance_to_bins

ROOT = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser()
p.add_argument("--api", default="http://127.0.0.1:8000")
p.add_argument("--threshold", type=float, default=150)
p.add_argument("--output", type=Path, default=ROOT / "data" / "accessibility.geojson")
args = p.parse_args()


def get(route):
    r = httpx.get(args.api + route, timeout=30)
    r.raise_for_status()
    return r.json()


pilot = get("/api/pilot")
streets = get("/api/streets")["features"]
bins = get("/api/bins")["features"]
project = Transformer.from_crs(4326, 32645, always_xy=True).transform
unproject = Transformer.from_crs(32645, 4326, always_xy=True).transform
graph = ox.convert.to_undirected(
    ox.project_graph(
        ox.load_graphml(ROOT / "data" / "pilot" / "network.graphml"),
        to_crs="EPSG:32645",
    )
)
points = [
    transform(project, shape(f["geometry"]))
    for f in bins
    if f["properties"]["status"] == "verified_usable"
]
features = []
for f in streets:
    line = transform(project, shape(f["geometry"]))
    samples = [
        line.interpolate(min(i * 25, line.length))
        for i in range(__import__("math").ceil(line.length / 25) + 1)
    ]
    for pt in samples:
        d = distance_to_bins(graph, pt, points)
        features.append(
            {
                "type": "Feature",
                "geometry": mapping(transform(unproject, pt)),
                "properties": {
                    "segment_id": f["properties"]["id"],
                    "inspection_status": f["properties"]["status"],
                    "distance_m": round(d, 1) if d is not None else None,
                    "threshold_m": args.threshold,
                    "assessment": "unknown"
                    if d is None
                    else (
                        "within_threshold"
                        if d <= args.threshold
                        else "beyond_threshold_to_known_bins"
                    ),
                    "provisional": pilot["anchor_status"] != "manually_verified",
                },
            }
        )
args.output.write_text(
    json.dumps(
        {
            "type": "FeatureCollection",
            "features": features,
            "metadata": {
                "method": "25 m samples, along-edge shortest paths to approved recent usable observations",
                "threshold_is_experimental": True,
                "limitations": "Known inventory only. No distance or missing record proves bin absence. Connector access unverified.",
            },
        },
        indent=2,
    )
)
print(f"Wrote {len(features)} samples to {args.output}")
