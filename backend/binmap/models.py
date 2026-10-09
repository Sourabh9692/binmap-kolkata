from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import JSON, String, Float, ForeignKey, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def now():
    return datetime.now(timezone.utc).isoformat()


class Base(DeclarativeBase):
    pass


class RecordMixin:
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    payload: Mapped[dict] = mapped_column(JSON)
    digest: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[str] = mapped_column(default=now)


class SurveySession(RecordMixin, Base):
    __tablename__ = "survey_sessions"


class Segment(Base):
    __tablename__ = "street_segments"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    geometry: Mapped[dict] = mapped_column(JSON)
    properties: Mapped[dict] = mapped_column(JSON)
    length_m: Mapped[float] = mapped_column(Float)


class Inspection(RecordMixin, Base):
    __tablename__ = "segment_inspections"
    session_id: Mapped[str] = mapped_column(ForeignKey("survey_sessions.id"))
    segment_id: Mapped[str] = mapped_column(ForeignKey("street_segments.id"))


class Observation(RecordMixin, Base):
    __tablename__ = "observations"
    session_id: Mapped[str] = mapped_column(ForeignKey("survey_sessions.id"))
    segment_id: Mapped[str] = mapped_column(ForeignKey("street_segments.id"))


class Evidence(Base):
    __tablename__ = "evidence_files"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    sha256: Mapped[str] = mapped_column(String(64))
    filename: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[str] = mapped_column(default=now)


class Review(Base):
    __tablename__ = "verification_reviews"
    id: Mapped[str] = mapped_column(
        String(80), primary_key=True, default=lambda: str(uuid4())
    )
    target_type: Mapped[str] = mapped_column(String(20))
    target_id: Mapped[str] = mapped_column(String(80), index=True)
    decision: Mapped[str] = mapped_column(String(20))
    reason: Mapped[str] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(default=now)


class Audit(Base):
    __tablename__ = "audit_events"
    id: Mapped[str] = mapped_column(
        String(80), primary_key=True, default=lambda: str(uuid4())
    )
    action: Mapped[str] = mapped_column(String(60))
    target_id: Mapped[str] = mapped_column(String(80))
    actor_role: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[str] = mapped_column(default=now)


class SourceRecord(Base):
    __tablename__ = "source_records"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    geometry: Mapped[dict] = mapped_column(JSON)
    properties: Mapped[dict] = mapped_column(JSON)
