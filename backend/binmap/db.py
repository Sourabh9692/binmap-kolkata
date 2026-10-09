from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker
from .models import Base


def connect(url):
    engine = create_engine(
        url,
        connect_args={"check_same_thread": False} if url.startswith("sqlite") else {},
    )
    if url.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def foreign_keys(conn, _):
            conn.execute("PRAGMA foreign_keys=ON")

    return engine, sessionmaker(engine, expire_on_commit=False)


def initialize(engine):
    Base.metadata.create_all(engine)
    if engine.dialect.name == "postgresql":
        with engine.begin() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
            for table in ("street_segments", "source_records"):
                conn.execute(
                    text(f"""ALTER TABLE {table} ADD COLUMN IF NOT EXISTS geom geometry(Geometry,4326)
                    GENERATED ALWAYS AS (ST_SetSRID(ST_GeomFromGeoJSON(geometry::text),4326)) STORED""")
                )
                conn.execute(
                    text(
                        f"CREATE INDEX IF NOT EXISTS ix_{table}_geom ON {table} USING GIST (geom)"
                    )
                )
            conn.execute(
                text(
                    "CREATE TABLE IF NOT EXISTS schema_version (version INTEGER PRIMARY KEY)"
                )
            )
            conn.execute(
                text("INSERT INTO schema_version VALUES (1) ON CONFLICT DO NOTHING")
            )
