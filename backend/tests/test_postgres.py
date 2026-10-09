import os
import pytest
from sqlalchemy import text
from binmap.db import connect, initialize
from binmap.models import Segment


@pytest.mark.skipif(
    not os.getenv("BINMAP_TEST_POSTGRES_URL"),
    reason="Requires dedicated PostGIS test database",
)
def test_postgis_generated_geometry_and_spatial_index():
    engine, Session = connect(os.environ["BINMAP_TEST_POSTGRES_URL"])
    initialize(engine)
    with Session.begin() as s:
        if not s.get(Segment, "postgis-fixture"):
            s.add(
                Segment(
                    id="postgis-fixture",
                    geometry={
                        "type": "LineString",
                        "coordinates": [[88.36, 22.49], [88.37, 22.49]],
                    },
                    properties={"test": True},
                    length_m=1000,
                )
            )
    with engine.connect() as conn:
        assert (
            conn.execute(
                text(
                    "SELECT ST_SRID(geom) FROM street_segments WHERE id='postgis-fixture'"
                )
            ).scalar()
            == 4326
        )
        assert conn.execute(
            text(
                "SELECT ST_Length(geom::geography)>900 FROM street_segments WHERE id='postgis-fixture'"
            )
        ).scalar()
        assert (
            conn.execute(
                text(
                    "SELECT count(*) FROM pg_indexes WHERE indexname='ix_street_segments_geom'"
                )
            ).scalar()
            == 1
        )
