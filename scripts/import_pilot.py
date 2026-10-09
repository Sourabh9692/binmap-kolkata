#!/usr/bin/env python3
"""Idempotently import generated files without modifying field evidence."""

import argparse, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from binmap.config import Settings
from binmap.db import connect, initialize
from binmap.models import Segment, SourceRecord


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--folder", type=Path, default=Settings().data_dir / "pilot")
    args = p.parse_args()
    cfg = Settings()
    engine, Session = connect(cfg.database_url)
    initialize(engine)
    count = 0
    with Session.begin() as session:
        for filename, model in [
            ("reachable_streets.geojson", Segment),
            ("osm_bins.geojson", SourceRecord),
        ]:
            for f in json.loads((args.folder / filename).read_text())["features"]:
                sid = str(f["properties"]["id"])
                existing = session.get(model, sid)
                if existing:
                    if existing.geometry != f["geometry"]:
                        raise ValueError(
                            f"Geometry changed for {sid}; create a versioned pilot"
                        )
                    continue
                values = {
                    "id": sid,
                    "geometry": f["geometry"],
                    "properties": f["properties"],
                }
                if model is Segment:
                    values["length_m"] = f["properties"]["length_m"]
                session.add(model(**values))
                count += 1
    print(f"Imported {count} new records. Existing records preserved.")


if __name__ == "__main__":
    main()
