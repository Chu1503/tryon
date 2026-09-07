from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.models import Garment, GenerationStatus


class GarmentResponse(BaseModel):
    id: str
    name: str
    brand: str | None
    category: str
    color: str | None
    raw_front_url: str
    raw_back_url: str | None
    clean_front_url: str | None
    clean_back_url: str | None
    tryon_front_url: str | None
    tryon_back_url: str | None
    tryon_front_cutout_url: str | None
    tryon_back_cutout_url: str | None
    front_status: GenerationStatus
    back_status: GenerationStatus
    front_progress: int
    back_progress: int
    front_progress_stage: str | None
    back_progress_stage: str | None
    front_error: str | None
    back_error: str | None
    garment_version: int
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_model(
        cls,
        garment: Garment,
        progress: dict[str, int] | None = None,
        stages: dict[str, str] | None = None,
    ) -> "GarmentResponse":
        base = f"/api/assets/garments/{garment.id}"
        progress = progress or {}
        stages = stages or {}

        def view_progress(view: str) -> int:
            status = getattr(garment, f"{view}_status")
            if status == GenerationStatus.READY:
                return 100
            if status == GenerationStatus.PROCESSING:
                return progress.get(view, 1)
            return 0

        return cls(
            id=garment.id,
            name=garment.name,
            brand=garment.brand,
            category=garment.category,
            color=garment.color,
            raw_front_url=f"{base}/raw_front",
            raw_back_url=f"{base}/raw_back" if garment.raw_back_path else None,
            clean_front_url=f"{base}/clean_front" if garment.clean_front_path else None,
            clean_back_url=f"{base}/clean_back" if garment.clean_back_path else None,
            tryon_front_url=f"/api/garments/{garment.id}/tryon/front" if garment.tryon_front_path else None,
            tryon_back_url=f"/api/garments/{garment.id}/tryon/back" if garment.tryon_back_path else None,
            tryon_front_cutout_url=(
                f"{base}/tryon_front_cutout" if garment.tryon_front_cutout_path else None
            ),
            tryon_back_cutout_url=(
                f"{base}/tryon_back_cutout" if garment.tryon_back_cutout_path else None
            ),
            front_status=garment.front_status,
            back_status=garment.back_status,
            front_progress=view_progress("front"),
            back_progress=view_progress("back"),
            front_progress_stage=stages.get("front") if garment.front_status == GenerationStatus.PROCESSING else None,
            back_progress_stage=stages.get("back") if garment.back_status == GenerationStatus.PROCESSING else None,
            front_error=garment.front_error,
            back_error=garment.back_error,
            garment_version=garment.garment_version,
            created_at=garment.created_at,
            updated_at=garment.updated_at,
        )


class GenerationResponse(BaseModel):
    garment: GarmentResponse
    queued_views: list[str]
    cached_views: list[str]
