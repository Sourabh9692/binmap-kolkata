#!/usr/bin/env python3
"""Download a real OSM walk network; never create field observations."""

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
import geopandas as gpd
import osmnx as ox
from pyproj import Transformer
from shapely.geometry import Point, mapping
from shapely.ops import transform, substring, unary_union
from binmap.geo import catchment

ROOT = Path(__file__).resolve().parents[1]


def write(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, default=str) + "\n")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--osm-xml", type=Path, help="Process a saved OSM XML extract without Overpass"
    )
    p.add_argument("--lat", required=True, type=float)
    p.add_argument("--lon", required=True, type=float)
    p.add_argument("--source", required=True)
    p.add_argument("--overpass-url", default="https://overpass-api.de/api")
    p.add_argument(
        "--anchor-verified",
        action="store_true",
        help="Only after manually confirming the public entrance",
    )
    p.add_argument(
        "--user-confirmed-pin",
        action="store_true",
        help="User selected a map pin; entrance access still requires field checking",
    )
    p.add_argument("--distance", type=float, default=500)
    p.add_argument("--output", type=Path, default=ROOT / "data" / "pilot")
    args = p.parse_args()
    if not (22 < args.lat < 23 and 88 < args.lon < 89 and 0 < args.distance <= 2000):
        p.error("Expected a Kolkata coordinate and a catchment between 0 and 2000 m")
    folder = args.output
    if (folder / "metadata.json").exists():
        p.error(
            "Output already contains a pilot. Use a new --output folder to preserve provenance."
        )
    folder.mkdir(parents=True, exist_ok=True)
    ox.settings.use_cache = True
    ox.settings.cache_folder = str(ROOT / "data" / "osm-cache")
    ox.settings.requests_timeout = 45
    ox.settings.overpass_url = args.overpass_url
    ox.settings.log_console = True
    ox.settings.http_user_agent = "BinMapKolkata/0.1 civic pilot (local research)"
    extent = args.distance + 700
    xml_bins = []
    if args.osm_xml:
        import xml.etree.ElementTree as ET

        tree = ET.parse(args.osm_xml)
        root = tree.getroot()
        coords = {
            node.attrib["id"]: (float(node.attrib["lon"]), float(node.attrib["lat"]))
            for node in root.findall("node")
        }
        excluded = {
            "motorway",
            "motorway_link",
            "trunk",
            "trunk_link",
            "construction",
            "proposed",
            "raceway",
            "abandoned",
            "platform",
            "bus_guideway",
            "cycleway",
        }
        for element in list(root):
            tags = {t.attrib["k"]: t.attrib["v"] for t in element.findall("tag")}
            if (
                tags.get("amenity") in {"waste_basket", "waste_disposal", "recycling"}
                or tags.get("bin") == "yes"
            ):
                point = None
                if element.tag == "node":
                    point = coords[element.attrib["id"]]
                elif element.tag == "way":
                    locations = [
                        coords[n.attrib["ref"]]
                        for n in element.findall("nd")
                        if n.attrib["ref"] in coords
                    ]
                    if locations:
                        point = (
                            sum(x for x, y in locations) / len(locations),
                            sum(y for x, y in locations) / len(locations),
                        )
                if point:
                    sid = f"osm-{element.tag}-{element.attrib['id']}"
                    xml_bins.append(
                        {
                            "type": "Feature",
                            "id": sid,
                            "geometry": {"type": "Point", "coordinates": point},
                            "properties": {
                                "id": sid,
                                "source": f"https://www.openstreetmap.org/{element.tag}/{element.attrib['id']}",
                                "tags": tags,
                                "status": "osm_unverified",
                                "position_method": "OSM node"
                                if element.tag == "node"
                                else "vertex mean; inspect geometry",
                            },
                        }
                    )
            if element.tag == "way" and (
                not tags.get("highway")
                or tags.get("highway") in excluded
                or tags.get("area") == "yes"
                or tags.get("foot") in {"no", "private"}
                or tags.get("access") in {"private", "no"}
                or tags.get("service") == "private"
            ):
                root.remove(element)
            elif element.tag == "relation":
                root.remove(element)
        filtered = folder / "walk-filtered.osm"
        tree.write(filtered, encoding="utf-8", xml_declaration=True)
        raw = ox.graph_from_xml(
            filtered, bidirectional=True, simplify=True, retain_all=True
        )
        raw.remove_nodes_from(list(__import__("networkx").isolates(raw)))
    else:
        raw = ox.graph_from_point(
            (args.lat, args.lon),
            dist=extent,
            network_type="walk",
            retain_all=True,
            truncate_by_edge=True,
        )
    ox.save_graphml(raw, folder / "network.graphml")
    graph = ox.convert.to_undirected(ox.project_graph(raw, to_crs="EPSG:32645"))
    project = Transformer.from_crs(4326, 32645, always_xy=True).transform
    unproject = Transformer.from_crs(32645, 4326, always_xy=True).transform
    lines, offset = catchment(
        graph, transform(project, Point(args.lon, args.lat)), args.distance
    )
    features = []
    for line, props in lines:
        for i in range(max(1, __import__("math").ceil(line.length / 100))):
            piece = substring(line, i * 100, min(line.length, (i + 1) * 100))
            if piece.length < 0.01:
                continue
            geom = mapping(transform(unproject, piece))
            sid = hashlib.sha256(json.dumps(geom, sort_keys=True).encode()).hexdigest()[
                :20
            ]
            features.append(
                {
                    "type": "Feature",
                    "id": sid,
                    "geometry": geom,
                    "properties": {
                        **props,
                        "id": sid,
                        "length_m": round(piece.length, 3),
                        "status": "unsurveyed",
                    },
                }
            )
    write(
        folder / "reachable_streets.geojson",
        {"type": "FeatureCollection", "features": features},
    )
    polygon = unary_union([line for line, _ in lines]).buffer(15)
    write(
        folder / "pilot_boundary.geojson",
        {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": mapping(transform(unproject, polygon)),
                    "properties": {"display_only": True, "buffer_m": 15},
                }
            ],
        },
    )
    bins = xml_bins
    bin_status = "from_osm_xml_nodes_and_ways" if args.osm_xml else "downloaded"
    try:
        points = (
            gpd.GeoDataFrame()
            if args.osm_xml
            else ox.features_from_point(
                (args.lat, args.lon),
                tags={
                    "amenity": ["waste_basket", "waste_disposal", "recycling"],
                    "bin": "yes",
                },
                dist=extent,
            )
        )
        for (kind, oid), row in points.iterrows():
            geom = row.geometry
            if geom.geom_type != "Point":
                geom = geom.representative_point()
            tags = {
                str(k): str(v)
                for k, v in row.items()
                if k != "geometry"
                and not isinstance(v, (list, dict))
                and not __import__("pandas").isna(v)
            }
            bins.append(
                {
                    "type": "Feature",
                    "id": f"osm-{kind}-{oid}",
                    "geometry": mapping(geom),
                    "properties": {
                        "id": f"osm-{kind}-{oid}",
                        "source": f"https://www.openstreetmap.org/{kind}/{oid}",
                        "status": "osm_unverified",
                        "tags": tags,
                    },
                }
            )
    except ox._errors.InsufficientResponseError:
        bin_status = "no_matching_osm_records"
    except Exception as exc:
        bin_status = f"download_failed:{type(exc).__name__}"
        print(f"Bin extraction incomplete: {exc}", file=sys.stderr)
    write(folder / "osm_bins.geojson", {"type": "FeatureCollection", "features": bins})
    metadata = {
        "name": "Narkelbagan Kali Mandir",
        "center": [args.lon, args.lat],
        "center_is_candidate": not (args.anchor_verified or args.user_confirmed_pin),
        "anchor_status": "manually_verified"
        if args.anchor_verified
        else (
            "user_confirmed_map_pin"
            if args.user_confirmed_pin
            else "candidate_unverified"
        ),
        "source": args.source,
        "ward": None,
        "ward_status": "unverified",
        "catchment_m": args.distance,
        "network_status": "downloaded",
        "osm_bin_status": bin_status,
        "download_method": "OSM map API XML" if args.osm_xml else "Overpass",
        "osm_source_sha256": hashlib.sha256(args.osm_xml.read_bytes()).hexdigest()
        if args.osm_xml
        else None,
        "download_extent_m": None if args.osm_xml else extent,
        "xml_bounds": dict(root.find("bounds").attrib)
        if args.osm_xml and root.find("bounds") is not None
        else None,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "anchor_snap_offset_m": round(offset, 3),
        "segment_count": len(features),
        "network_m": round(sum(f["properties"]["length_m"] for f in features), 2),
        "network_sha256": hashlib.sha256(
            (folder / "network.graphml").read_bytes()
        ).hexdigest(),
        "license": "OpenStreetMap contributors, ODbL 1.0",
        "field_observations": 0,
        "limitations": [
            "Street access and anchor-to-edge connector require field verification",
            "Boundary is a 15 m visualization buffer, not a ward boundary",
            "No matching OSM bins is not evidence of absence",
            "Distances use projected OSM geometry; barriers or missing paths may affect reachability",
            "XML fallback excludes relations from bin inventory; inventory is incomplete",
        ],
    }
    write(folder / "metadata.json", metadata)
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
