#!/usr/bin/env python3
"""Single small-area OSM API download, saved for reproducible offline processing."""

import argparse
from pathlib import Path
import httpx

p = argparse.ArgumentParser()
p.add_argument("--output", type=Path, default=Path("data/pilot/source.osm"))
p.add_argument("--bbox", default="88.352,22.476,88.383,22.507")
a = p.parse_args()
if a.output.exists():
    raise SystemExit("Existing source preserved; use another output path.")
r = httpx.get(
    "https://api.openstreetmap.org/api/0.6/map",
    params={"bbox": a.bbox},
    headers={"User-Agent": "BinMapKolkata/0.1 civic research pilot"},
    timeout=60,
    follow_redirects=True,
)
if r.status_code != 200:
    raise SystemExit(f"OSM {r.status_code}: {r.text[:600]}")
a.output.parent.mkdir(parents=True, exist_ok=True)
a.output.write_bytes(r.content)
print(f"Saved {len(r.content)} bytes of actual OSM XML to {a.output}")
