#!/usr/bin/env python3
"""Attribute an anchor using an explicitly supplied authoritative WGS84 ward dataset."""

import argparse, hashlib, json
from pathlib import Path
from shapely.geometry import Point, shape
from shapely.ops import transform
from pyproj import Transformer

p = argparse.ArgumentParser()
p.add_argument("wards", type=Path)
p.add_argument(
    "--source", required=True, help="Authoritative publisher URL or document reference"
)
p.add_argument("--ward-property", default="ward")
p.add_argument("--pilot", type=Path, default=Path("data/pilot"))
a = p.parse_args()
metadata = json.loads((a.pilot / "metadata.json").read_text())
data = json.loads(a.wards.read_text())
if data.get("crs"):
    raise SystemExit(
        "Normalize the ward GeoJSON to RFC 7946 WGS84 with no crs member first."
    )
point = Point(*metadata["center"])
project = Transformer.from_crs(4326, 32645, always_xy=True).transform
matches = []
for f in data["features"]:
    poly = shape(f["geometry"])
    if not poly.is_valid or poly.geom_type not in {"Polygon", "MultiPolygon"}:
        raise SystemExit("Ward dataset must contain valid polygon geometries.")
    if poly.covers(point):
        matches.append(
            (
                str(f["properties"][a.ward_property]),
                transform(project, poly.boundary).distance(transform(project, point)),
            )
        )
if len(matches) != 1 or matches[0][1] < 15:
    raise SystemExit(
        f"Ambiguous boundary attribution; manual review required: {matches}"
    )
metadata.update(
    ward=matches[0][0],
    ward_status="verified_against_supplied_boundary",
    ward_source=a.source,
    ward_dataset_sha256=hashlib.sha256(a.wards.read_bytes()).hexdigest(),
    ward_boundary_distance_m=round(matches[0][1], 2),
)
(a.pilot / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
print(f"Anchor falls in ward {matches[0][0]}. Catchment may cross other wards.")
