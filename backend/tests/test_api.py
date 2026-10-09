import io
from datetime import datetime, timezone, timedelta
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from PIL import Image
from binmap.config import Settings
from binmap.main import create_app
from binmap.models import Segment

SURVEY = {"Authorization": "Bearer test-survey"}
REVIEW = {"Authorization": "Bearer test-review"}


def stamp():
    return datetime.now(timezone.utc).isoformat()


@pytest.fixture
def client(tmp_path):
    cfg = Settings(
        _env_file=None,
        database_url=f"sqlite:///{tmp_path}/test.db",
        data_dir=tmp_path,
        survey_key="test-survey",
        review_key="test-review",
        frontend_dir=tmp_path / "absent",
    )
    app = create_app(cfg)
    with TestClient(app) as c:
        with app.state.session.begin() as s:
            s.add(
                Segment(
                    id="test-street",
                    geometry={
                        "type": "LineString",
                        "coordinates": [[88.367, 22.491], [88.368, 22.491]],
                    },
                    properties={"name": "TEST FIXTURE ONLY"},
                    length_m=100,
                )
            )
        yield c


def session(client):
    body = {
        "id": str(uuid4()),
        "surveyor": "fixture-only",
        "started_at": stamp(),
        "consent": True,
    }
    assert client.post("/api/sessions", json=body, headers=SURVEY).status_code == 200
    return body["id"]


def inspection(client, **overrides):
    body = {
        "id": str(uuid4()),
        "session_id": session(client),
        "segment_id": "test-street",
        "observed_at": stamp(),
        "sides": "both",
        "visibility": "clear",
        "coverage": 1,
        "result": "no_bin_observed",
        "notes": "private fixture note",
    }
    body.update(overrides)
    return body


def photo(client):
    stream = io.BytesIO()
    Image.new("RGB", (20, 20), "blue").save(
        stream, format="JPEG", exif=b"Exif\x00\x00private"
    )
    eid = str(uuid4())
    assert (
        client.put(
            "/api/evidence/" + eid,
            files={"file": ("x.jpg", stream.getvalue(), "image/jpeg")},
            headers=SURVEY,
        ).status_code
        == 200
    )
    return eid


def observation(client, **overrides):
    body = {
        "id": str(uuid4()),
        "session_id": session(client),
        "segment_id": "test-street",
        "observed_at": stamp(),
        "latitude": 22.491,
        "longitude": 88.3675,
        "accuracy_m": 5,
        "category": "public_litter_bin",
        "condition": "usable",
        "public_access": True,
        "evidence_id": photo(client),
        "notes": "private fixture note",
    }
    body.update(overrides)
    return body


def review(client, body, kind="inspection", decision="approved"):
    return client.post(
        "/api/reviews",
        headers=REVIEW,
        json={
            "target_type": kind,
            "target_id": body["id"],
            "decision": decision,
            "reason": "Checked synthetic test evidence",
        },
    )


def test_auth_and_role_separation(client):
    assert client.get("/api/health").status_code == 200
    assert client.get("/api/review-queue").status_code == 401
    assert client.get("/api/review-queue", headers=SURVEY).status_code == 401
    body = {
        "id": str(uuid4()),
        "surveyor": "test",
        "started_at": stamp(),
        "consent": True,
    }
    assert client.post("/api/sessions", json=body, headers=REVIEW).status_code == 401
    assert client.post("/api/sessions", json=body).status_code == 401


def test_immutable_retry_and_conflict(client):
    body = inspection(client)
    assert (
        client.post("/api/inspections", json=body, headers=SURVEY).json()["duplicate"]
        is False
    )
    assert (
        client.post("/api/inspections", json=body, headers=SURVEY).json()["duplicate"]
        is True
    )
    body["notes"] = "changed"
    assert client.post("/api/inspections", json=body, headers=SURVEY).status_code == 409


@pytest.mark.parametrize(
    "changes",
    [
        {"sides": "left"},
        {"visibility": "partial"},
        {"coverage": 0.94},
        {"result": "unable_to_inspect", "sides": "neither"},
    ],
)
def test_incomplete_is_never_complete_coverage(client, changes):
    body = inspection(client, **changes)
    assert client.post("/api/inspections", json=body, headers=SURVEY).status_code == 200
    result = review(client, body)
    if body["result"] == "no_bin_observed":
        assert result.status_code == 422
    assert client.get("/api/summary").json()["coverage_percent"] == 0


def test_coverage_requires_approval_and_freshness(client):
    body = inspection(client)
    client.post("/api/inspections", json=body, headers=SURVEY)
    assert client.get("/api/summary").json()["coverage_percent"] == 0
    assert review(client, body).status_code == 200
    assert client.get("/api/summary").json()["coverage_percent"] == 100
    assert (
        client.get("/api/streets").json()["features"][0]["properties"]["status"]
        == "inspected"
    )
    assert review(client, body, decision="rejected").status_code == 200
    assert client.get("/api/summary").json()["coverage_percent"] == 0


def test_old_inspection_needs_recheck(client):
    body = inspection(
        client,
        observed_at=(datetime.now(timezone.utc) - timedelta(days=31)).isoformat(),
    )
    client.post("/api/inspections", json=body, headers=SURVEY)
    review(client, body)
    assert (
        client.get("/api/streets").json()["features"][0]["properties"]["status"]
        == "needs_recheck"
    )


def test_photo_is_private_and_metadata_stripped(client):
    eid = photo(client)
    assert client.get("/api/evidence/" + eid).status_code == 401
    response = client.get("/api/evidence/" + eid, headers=REVIEW)
    assert response.status_code == 200
    assert not Image.open(io.BytesIO(response.content)).getexif()
    assert response.headers["cache-control"] == "no-store"


def test_observation_approval_and_public_redaction(client):
    body = observation(client)
    assert (
        client.post("/api/observations", json=body, headers=SURVEY).status_code == 200
    )
    assert client.get("/api/bins").json()["features"] == []
    assert review(client, body, "observation").status_code == 200
    result = client.get("/api/export")
    assert "private fixture note" not in result.text
    assert "fixture-only" not in result.text
    assert body["evidence_id"] not in result.text
    assert client.get("/api/summary").json()["verified_usable_observations"] == 1


@pytest.mark.parametrize("condition", ["overflowing", "damaged", "blocked", "missing"])
def test_unusable_bins_not_counted(client, condition):
    body = observation(client, condition=condition)
    client.post("/api/observations", json=body, headers=SURVEY)
    review(client, body, "observation")
    assert client.get("/api/summary").json()["verified_usable_observations"] == 0


def test_uncertain_gps_cannot_be_approved(client):
    body = observation(client, accuracy_m=30)
    assert (
        client.post("/api/observations", json=body, headers=SURVEY).status_code == 200
    )
    assert review(client, body, "observation").status_code == 422


def test_bad_reference_and_remote_coordinate(client):
    body = observation(client, segment_id="missing")
    assert (
        client.post("/api/observations", json=body, headers=SURVEY).status_code == 422
    )
    body.update(segment_id="test-street", latitude=22.8)
    assert (
        client.post("/api/observations", json=body, headers=SURVEY).status_code == 422
    )
    body["latitude"] = 91
    assert (
        client.post("/api/observations", json=body, headers=SURVEY).status_code == 422
    )


def test_future_and_naive_timestamps_rejected(client):
    for value in [
        "2026-01-01T12:00:00",
        (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
    ]:
        body = inspection(client, observed_at=value)
        assert (
            client.post("/api/inspections", json=body, headers=SURVEY).status_code
            == 422
        )


def test_upload_validation_and_immutability(client):
    eid = str(uuid4())
    assert (
        client.put(
            "/api/evidence/" + eid,
            files={"file": ("bad.jpg", b"not an image")},
            headers=SURVEY,
        ).status_code
        == 422
    )
    assert (
        client.put(
            "/api/evidence/" + eid,
            files={"file": ("big.jpg", b"x" * (8 * 1024 * 1024 + 1))},
            headers=SURVEY,
        ).status_code
        == 413
    )
    eid = photo(client)
    stream = io.BytesIO()
    Image.new("RGB", (20, 20), "red").save(stream, format="JPEG")
    assert (
        client.put(
            "/api/evidence/" + eid,
            files={"file": ("new.jpg", stream.getvalue())},
            headers=SURVEY,
        ).status_code
        == 409
    )


def test_missing_configuration_fails_closed(tmp_path):
    app = create_app(
        Settings(
            _env_file=None,
            database_url=f"sqlite:///{tmp_path}/test.db",
            data_dir=tmp_path,
            survey_key="",
            review_key="",
        )
    )
    with TestClient(app) as c:
        assert c.get("/api/review-queue").status_code == 503
