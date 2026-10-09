#!/usr/bin/env python3
"""One deliberate Nominatim lookup; results are candidates, not verified anchors."""

import argparse, json
import httpx

p = argparse.ArgumentParser()
p.add_argument("--query", default="Narkel Bagan Kali Mandir, Jadavpur, Kolkata")
args = p.parse_args()
r = httpx.get(
    "https://nominatim.openstreetmap.org/search",
    params={"q": args.query, "format": "jsonv2", "limit": 5},
    headers={"User-Agent": "BinMapKolkata/0.1 (single pilot research lookup)"},
    timeout=30,
)
r.raise_for_status()
print(json.dumps(r.json(), indent=2))
