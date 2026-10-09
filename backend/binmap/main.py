import hashlib
import io
import json
import secrets
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
from uuid import UUID

from fastapi import FastAPI, Depends, Header, HTTPException, UploadFile, File
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from pyproj import Transformer
from shapely.geometry import shape, Point
from shapely.ops import transform

from .config import Settings
from .db import connect, initialize
from .models import (
    SurveySession,
    Segment,
    Inspection,
    Observation,
    Evidence,
    Review,
    Audit,
    SourceRecord,
)
from .schemas import SessionIn, InspectionIn, ObservationIn, ReviewIn

PROJECT = Transformer.from_crs(4326, 32645, always_xy=True).transform
EMPTY = {"type": "FeatureCollection", "features": []}


def create_app(settings=None):
    cfg = settings or Settings()
    cfg.data_dir.mkdir(parents=True, exist_ok=True)
    engine, Session = connect(cfg.database_url)

    @asynccontextmanager
    async def lifespan(app):
        initialize(engine)
        yield
        engine.dispose()

    app = FastAPI(title="BinMap Kolkata", version="0.1.0", lifespan=lifespan)
    app.state.session = Session
    app.state.settings = cfg

    def db():
        with Session() as session:
            yield session

    def authorize(key, expected):
        if not expected:
            raise HTTPException(
                503, "Write access is not configured. Run scripts/setup_local.py."
            )
        if not key or not secrets.compare_digest(key, expected):
            raise HTTPException(401, "A valid access key is required")

    def survey(authorization: str = Header(default="")):
        authorize(authorization.removeprefix("Bearer "), cfg.survey_key)

    def reviewer(authorization: str = Header(default="")):
        authorize(authorization.removeprefix("Bearer "), cfg.review_key)

    def record(session, model, body, **fields):
        payload = body.model_dump(mode="json")
        digest = hashlib.sha256(
            json.dumps(payload, sort_keys=True).encode()
        ).hexdigest()
        record_id = str(body.id)
        existing = session.get(model, record_id)
        if existing:
            if existing.digest != digest:
                raise HTTPException(
                    409,
                    "This ID already belongs to different evidence; create a new record",
                )
            return {"id": record_id, "duplicate": True}
        session.add(model(id=record_id, payload=payload, digest=digest, **fields))
        session.add(
            Audit(
                action=f"create:{model.__tablename__}",
                target_id=record_id,
                actor_role="surveyor",
            )
        )
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            existing = session.get(model, record_id)
            if existing and existing.digest == digest:
                return {"id": record_id, "duplicate": True}
            raise HTTPException(
                409, "Concurrent record conflict; retry with the same payload"
            )
        return {"id": record_id, "duplicate": False}

    def references(session, body):
        if not session.get(SurveySession, str(body.session_id)):
            raise HTTPException(422, "Survey session not found")
        segment = session.get(Segment, body.segment_id)
        if not segment:
            raise HTTPException(422, "Unknown street segment; import the pilot first")
        return segment

    def latest_reviews(session):
        return {
            (r.target_type, r.target_id): r
            for r in session.scalars(
                select(Review).order_by(Review.created_at, Review.id)
            )
        }

    def fresh(payload):
        return datetime.fromisoformat(payload["observed_at"]) >= datetime.now(
            timezone.utc
        ) - timedelta(days=cfg.stale_days)

    def complete(p):
        return (
            p["sides"] == "both"
            and p["visibility"] == "clear"
            and p["coverage"] >= 0.95
            and p["result"] != "unable_to_inspect"
        )

    @app.get("/api/health")
    def health():
        return {"status": "ok", "version": "0.1.0", "storage": engine.dialect.name}

    @app.get("/api/pilot")
    def pilot():
        path = cfg.data_dir / "pilot" / "metadata.json"
        return (
            json.loads(path.read_text())
            if path.exists()
            else {
                "name": "Narkelbagan Kali Mandir",
                "catchment_m": 500,
                "anchor_status": "unverified",
                "ward_status": "unverified",
                "network_status": "not_imported",
                "center": [88.3677315, 22.4909012],
                "center_is_candidate": True,
                "source": "https://maps.app.goo.gl/fjJ3G3CQi7iCdz4h7",
            }
        )

    @app.get("/api/boundary")
    def boundary():
        path = cfg.data_dir / "pilot" / "pilot_boundary.geojson"
        return json.loads(path.read_text()) if path.exists() else EMPTY

    @app.get("/api/streets")
    def streets(session=Depends(db)):
        reviews = latest_reviews(session)
        inspections = {}
        for row in session.scalars(select(Inspection).order_by(Inspection.created_at)):
            review = reviews.get(("inspection", row.id))
            if review and review.decision == "approved":
                inspections.setdefault(row.segment_id, []).append(row.payload)
        features = []
        for s in session.scalars(select(Segment)):
            entries = inspections.get(s.id, [])
            p = max(entries, key=lambda p: p["observed_at"]) if entries else None
            status = "unsurveyed"
            if p:
                status = (
                    "needs_recheck"
                    if not fresh(p)
                    else ("inspected" if complete(p) else "partial")
                )
            features.append(
                {
                    "type": "Feature",
                    "id": s.id,
                    "geometry": s.geometry,
                    "properties": {
                        **s.properties,
                        "id": s.id,
                        "length_m": s.length_m,
                        "status": status,
                        "last_inspected_at": p["observed_at"] if p else None,
                        "finding": p["result"] if p and status == "inspected" else None,
                    },
                }
            )
        return {"type": "FeatureCollection", "features": features}

    @app.get("/api/bins")
    def bins(session=Depends(db)):
        reviews = latest_reviews(session)
        features = [
            {
                "type": "Feature",
                "id": s.id,
                "geometry": s.geometry,
                "properties": {**s.properties, "id": s.id, "status": "osm_unverified"},
            }
            for s in session.scalars(select(SourceRecord))
        ]
        for o in session.scalars(select(Observation)):
            r = reviews.get(("observation", o.id))
            if not r or r.decision != "approved":
                continue
            p = o.payload
            # These are observations, not deduplicated counts of physical assets.
            usable = (
                p["category"] == "public_litter_bin"
                and p["condition"] == "usable"
                and p["public_access"]
            )
            features.append(
                {
                    "type": "Feature",
                    "id": o.id,
                    "geometry": {
                        "type": "Point",
                        "coordinates": [p["longitude"], p["latitude"]],
                    },
                    "properties": {
                        "id": o.id,
                        "status": "needs_recheck"
                        if not fresh(p)
                        else ("verified_usable" if usable else "verified_other"),
                        "category": p["category"],
                        "condition": p["condition"],
                        "observed_at": p["observed_at"],
                        "public_access": p["public_access"],
                        "accuracy_m": p["accuracy_m"],
                    },
                }
            )
        return {"type": "FeatureCollection", "features": features}

    @app.get("/api/summary")
    def summary(session=Depends(db)):
        sf = streets(session)["features"]
        bf = bins(session)["features"]
        total = sum(f["properties"]["length_m"] for f in sf)
        inspected = sum(
            f["properties"]["length_m"]
            for f in sf
            if f["properties"]["status"] == "inspected"
        )
        return {
            "street_segments": len(sf),
            "network_m": round(total, 1),
            "inspected_m": round(inspected, 1),
            "coverage_percent": round(100 * inspected / total, 1) if total else 0,
            "verified_usable_observations": sum(
                f["properties"]["status"] == "verified_usable" for f in bf
            ),
            "osm_candidates": sum(
                f["properties"]["status"] == "osm_unverified" for f in bf
            ),
            "absence_claim": "No citywide or underserved-area claim is established by this inventory.",
            "freshness_days": cfg.stale_days,
        }

    @app.post("/api/sessions", dependencies=[Depends(survey)])
    def create_session(body: SessionIn, session=Depends(db)):
        return record(session, SurveySession, body)

    @app.post("/api/inspections", dependencies=[Depends(survey)])
    def inspect(body: InspectionIn, session=Depends(db)):
        references(session, body)
        return record(
            session,
            Inspection,
            body,
            session_id=str(body.session_id),
            segment_id=body.segment_id,
        )

    @app.post("/api/observations", dependencies=[Depends(survey)])
    def observe(body: ObservationIn, session=Depends(db)):
        segment = references(session, body)
        if not session.get(Evidence, str(body.evidence_id)):
            raise HTTPException(422, "Photo evidence must be uploaded first")
        distance = transform(PROJECT, shape(segment.geometry)).distance(
            transform(PROJECT, Point(body.longitude, body.latitude))
        )
        if distance > 100:
            raise HTTPException(
                422, "Location is more than 100 m from the selected segment"
            )
        return record(
            session,
            Observation,
            body,
            session_id=str(body.session_id),
            segment_id=body.segment_id,
        )

    @app.put("/api/evidence/{evidence_id}", dependencies=[Depends(survey)])
    async def upload(
        evidence_id: UUID, file: UploadFile = File(...), session=Depends(db)
    ):
        raw = await file.read(8 * 1024 * 1024 + 1)
        if len(raw) > 8 * 1024 * 1024:
            raise HTTPException(413, "Photos must be no larger than 8 MB")
        try:
            with Image.open(io.BytesIO(raw)) as source:
                if source.width * source.height > 25_000_000:
                    raise ValueError("Image too large")
                clean = ImageOps.exif_transpose(source).convert("RGB")
                clean.thumbnail((1920, 1920))
                out = io.BytesIO()
                clean.save(out, format="JPEG", quality=85)
                data = out.getvalue()
        except (
            UnidentifiedImageError,
            OSError,
            ValueError,
            Image.DecompressionBombError,
        ):
            raise HTTPException(
                422, "A valid image of at most 25 megapixels is required"
            )
        digest = hashlib.sha256(data).hexdigest()
        eid = str(evidence_id)
        existing = session.get(Evidence, eid)
        if existing:
            if existing.sha256 != digest:
                raise HTTPException(409, "Evidence is immutable; use a new ID")
            return {"id": eid, "sha256": digest, "duplicate": True}
        folder = cfg.data_dir / "evidence"
        folder.mkdir(exist_ok=True)
        filename = f"{eid}-{digest}.jpg"
        (folder / filename).write_bytes(data)
        session.add(Evidence(id=eid, sha256=digest, filename=filename))
        session.add(
            Audit(action="upload:evidence", target_id=eid, actor_role="surveyor")
        )
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            existing = session.get(Evidence, eid)
            if not existing or existing.sha256 != digest:
                raise HTTPException(409, "Evidence ID conflict")
        return {"id": eid, "sha256": digest, "duplicate": False}

    @app.get("/api/evidence/{evidence_id}", dependencies=[Depends(reviewer)])
    def evidence(evidence_id: UUID, session=Depends(db)):
        e = session.get(Evidence, str(evidence_id))
        if not e:
            raise HTTPException(404, "Evidence not found")
        return FileResponse(
            cfg.data_dir / "evidence" / e.filename,
            media_type="image/jpeg",
            headers={"Cache-Control": "no-store"},
        )

    @app.get("/api/review-queue", dependencies=[Depends(reviewer)])
    def queue(session=Depends(db)):
        reviews = latest_reviews(session)
        return [
            {"target_type": kind, "id": r.id, "payload": r.payload}
            for kind, model in [
                ("observation", Observation),
                ("inspection", Inspection),
            ]
            for r in session.scalars(select(model))
            if (kind, r.id) not in reviews
        ]

    @app.post("/api/reviews", dependencies=[Depends(reviewer)])
    def review(body: ReviewIn, session=Depends(db)):
        model = Observation if body.target_type == "observation" else Inspection
        row = session.get(model, str(body.target_id))
        if not row:
            raise HTTPException(404, "Record not found")
        p = row.payload
        if body.decision == "approved":
            if model is Observation and p["accuracy_m"] > 15:
                raise HTTPException(
                    422, "GPS accuracy exceeds 15 m; collect a replacement observation"
                )
            if (
                model is Inspection
                and p["result"] == "no_bin_observed"
                and not complete(p)
            ):
                raise HTTPException(
                    422,
                    "Negative evidence requires both sides, clear visibility and at least 95% declared coverage",
                )
        item = Review(**body.model_dump(mode="json"))
        session.add(item)
        session.add(
            Audit(
                action=f"review:{body.decision}",
                target_id=str(body.target_id),
                actor_role="reviewer",
            )
        )
        session.commit()
        return {"id": item.id, "decision": item.decision}

    @app.get("/api/export")
    def export(session=Depends(db)):
        return JSONResponse(
            {
                "type": "FeatureCollection",
                "features": streets(session)["features"] + bins(session)["features"],
                "metadata": {
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "pilot": pilot(),
                    "summary": summary(session),
                    "license": "OSM-derived data: ODbL 1.0; field observations: no public license assigned yet",
                    "limitations": [
                        "Observations are not deduplicated physical assets",
                        "Private photos, surveyor identity and notes excluded",
                        "Inspection completeness is declared by the surveyor; no GPS track validation in v0.1",
                        "Network accessibility analysis is a separate CLI output; inspection alone is not proof of underserved status",
                    ],
                },
            },
            headers={
                "Content-Disposition": 'attachment; filename="binmap-public-evidence.geojson"'
            },
        )

    @app.middleware("http")
    async def security_headers(request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "same-origin"
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    if cfg.frontend_dir.exists():
        app.mount(
            "/", StaticFiles(directory=cfg.frontend_dir, html=True), name="frontend"
        )
    return app


app = create_app()
