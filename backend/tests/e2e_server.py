"""Isolated synthetic browser-test server. Never import into the real application DB."""

import tempfile
from pathlib import Path
from binmap.config import Settings
from binmap.db import connect, initialize
from binmap.models import Segment
from binmap.main import create_app

folder = Path(tempfile.mkdtemp(prefix="binmap-e2e-"))
cfg = Settings(
    _env_file=None,
    database_url=f"sqlite:///{folder}/test.db",
    data_dir=folder,
    survey_key="e2e-survey",
    review_key="e2e-review",
)
engine, Session = connect(cfg.database_url)
initialize(engine)
with Session.begin() as session:
    session.add(
        Segment(
            id="test-segment",
            geometry={
                "type": "LineString",
                "coordinates": [[88.367, 22.491], [88.368, 22.491]],
            },
            properties={"name": "Synthetic test street"},
            length_m=100,
        )
    )
app = create_app(cfg)
