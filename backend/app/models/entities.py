from __future__ import annotations

import enum
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class GenerationStatus(str, enum.Enum):
    NOT_GENERATED = "not_generated"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class AppSettings(Base):
    __tablename__ = "app_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    display_name: Mapped[str] = mapped_column(String(80), default="CHU", nullable=False)
    body_front_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    body_back_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    body_front_cutout_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    body_back_cutout_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    body_reference_version: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class Garment(Base):
    __tablename__ = "garments"
    __table_args__ = (
        Index("idx_garments_category_created", "category", "created_at"),
        Index("idx_garments_status", "front_status", "back_status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    brand: Mapped[str | None] = mapped_column(String(120), nullable=True)
    category: Mapped[str] = mapped_column(String(40), nullable=False)
    color: Mapped[str | None] = mapped_column(String(80), nullable=True)

    raw_front_path: Mapped[str] = mapped_column(String(512), nullable=False)
    raw_back_path: Mapped[str] = mapped_column(String(512), nullable=False)
    clean_front_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    clean_back_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    tryon_front_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    tryon_back_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    tryon_front_cutout_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    tryon_back_cutout_path: Mapped[str | None] = mapped_column(String(512), nullable=True)

    front_status: Mapped[GenerationStatus] = mapped_column(
        Enum(GenerationStatus, native_enum=False), default=GenerationStatus.NOT_GENERATED, nullable=False
    )
    back_status: Mapped[GenerationStatus] = mapped_column(
        Enum(GenerationStatus, native_enum=False), default=GenerationStatus.NOT_GENERATED, nullable=False
    )
    front_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    back_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    garment_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    front_image_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    back_image_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    tryon_front_garment_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tryon_back_garment_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tryon_front_body_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tryon_back_body_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tryon_front_profile: Mapped[str | None] = mapped_column(String(160), nullable=True)
    tryon_back_profile: Mapped[str | None] = mapped_column(String(160), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )
