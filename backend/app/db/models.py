from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base

# PostgreSQL-এ JSONB (দ্রুত, query করা যায়), SQLite-এ সাধারণ JSON (test-এর জন্য)
JSONType = JSON().with_variant(JSONB(), "postgresql")


def _now():
    return datetime.now(timezone.utc)


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    file_name: Mapped[str] = mapped_column(String(255))
    stored_path: Mapped[Optional[str]] = mapped_column(String(1000))
    file_hash: Mapped[Optional[str]] = mapped_column(String(64), index=True)
    invoice_key: Mapped[Optional[str]] = mapped_column(String(500), index=True)
    status: Mapped[str] = mapped_column(String(20), default="queued", index=True)
    needs_review: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    review_reasons: Mapped[Optional[list]] = mapped_column(JSONType)
    extracted_text: Mapped[Optional[str]] = mapped_column(Text)
    error: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    extraction: Mapped[Optional["Extraction"]] = relationship(
        back_populates="document", uselist=False, cascade="all, delete-orphan")
    issues: Mapped[list["ValidationIssue"]] = relationship(
        back_populates="document", cascade="all, delete-orphan")
    events: Mapped[list["ProcessingEvent"]] = relationship(
        back_populates="document", cascade="all, delete-orphan",
        order_by="ProcessingEvent.id")


class Extraction(Base):
    __tablename__ = "extractions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    result: Mapped[dict] = mapped_column(JSONType)               # AI-র মূল উত্তর (অপরিবর্তিত)
    corrected: Mapped[Optional[dict]] = mapped_column(JSONType)  # মানুষের সংশোধনসহ সংস্করণ
    provider: Mapped[Optional[str]] = mapped_column(String(100))
    file_seconds: Mapped[Optional[float]] = mapped_column()
    llm_seconds: Mapped[Optional[float]] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    document: Mapped["Document"] = relationship(back_populates="extraction")


class ValidationIssue(Base):
    __tablename__ = "validation_issues"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    type: Mapped[str] = mapped_column(String(50), index=True)
    field: Mapped[Optional[str]] = mapped_column(String(100))
    severity: Mapped[str] = mapped_column(String(10))            # error | warning
    message: Mapped[Optional[str]] = mapped_column(Text)
    expected: Mapped[Optional[str]] = mapped_column(String(200))
    actual: Mapped[Optional[str]] = mapped_column(String(200))
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)

    document: Mapped["Document"] = relationship(back_populates="issues")


class ProcessingEvent(Base):
    __tablename__ = "processing_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    event: Mapped[str] = mapped_column(String(50))
    message: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    document: Mapped["Document"] = relationship(back_populates="events")