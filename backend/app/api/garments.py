from __future__ import annotations

import shutil
import uuid
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_db, get_generation_manager, get_storage
from app.api.user import get_or_create_settings
from app.config import get_settings
from app.models import Garment, GenerationStatus
from app.schemas.garments import GarmentResponse, GenerationResponse
from app.services.garment_processor import GarmentProcessor
from app.services.generation_jobs import GenerationManager, is_cache_valid
from app.services.storage import LocalStorage


router = APIRouter(prefix="/garments", tags=["garments"])
CATEGORIES = {
    "T-Shirt", "Polo", "Shirt", "Sweater", "Hoodie", "Jacket",
    "Pants", "Jeans", "Shorts", "Sweatpants", "Other",
}


def clean_optional(value: str | None, limit: int = 120) -> str | None:
    if value is None:
        return None
    cleaned = " ".join(value.split()).strip()
    return cleaned[:limit] or None


def require_garment(db: Session, garment_id: str) -> Garment:
    garment = db.get(Garment, garment_id)
    if garment is None:
        raise HTTPException(404, "Garment not found.")
    return garment


def process_view(garment: Garment, view: str, storage: LocalStorage) -> None:
    settings = get_settings()
    raw = storage.resolve(getattr(garment, f"raw_{view}_path"))
    clean = storage.garment_dir(garment.id) / f"clean_{view}.png"
    try:
        GarmentProcessor(settings).process(raw, clean)
    except Exception as exc:
        setattr(garment, f"{view}_error", f"Preprocessing failed: {exc}")
        raise
    setattr(garment, f"clean_{view}_path", storage.relative(clean))
    setattr(garment, f"{view}_error", None)


@router.get("", response_model=list[GarmentResponse])
def list_garments(
    db: Session = Depends(get_db),
    manager: GenerationManager = Depends(get_generation_manager),
) -> list[GarmentResponse]:
    garments = db.scalars(select(Garment).order_by(Garment.created_at.desc())).all()
    return [
        GarmentResponse.from_model(item, manager.progress_for(item.id), manager.stages_for(item.id))
        for item in garments
    ]


@router.get("/{garment_id}", response_model=GarmentResponse)
def get_garment(
    garment_id: str,
    db: Session = Depends(get_db),
    manager: GenerationManager = Depends(get_generation_manager),
) -> GarmentResponse:
    garment = require_garment(db, garment_id)
    return GarmentResponse.from_model(
        garment,
        manager.progress_for(garment.id),
        manager.stages_for(garment.id),
    )


@router.post("", response_model=GarmentResponse, status_code=status.HTTP_201_CREATED)
async def create_garment(
    name: str = Form(...),
    category: str = Form(...),
    brand: str | None = Form(default=None),
    color: str | None = Form(default=None),
    front: UploadFile = File(...),
    back: UploadFile | None = File(default=None),
    db: Session = Depends(get_db),
    storage: LocalStorage = Depends(get_storage),
) -> GarmentResponse:
    cleaned_name = clean_optional(name)
    if not cleaned_name:
        raise HTTPException(422, "Garment name is required.")
    if category not in CATEGORIES:
        raise HTTPException(422, "Choose a supported garment category.")
    garment_id = str(uuid.uuid4())
    try:
        raw_front = await storage.save_upload(front, Path("garments") / garment_id / "raw_front")
        raw_back = (
            await storage.save_upload(back, Path("garments") / garment_id / "raw_back")
            if back is not None
            else ""
        )
        garment = Garment(
            id=garment_id, name=cleaned_name, brand=clean_optional(brand), category=category,
            color=clean_optional(color, 80), raw_front_path=raw_front, raw_back_path=raw_back,
        )
        db.add(garment)
        db.flush()
        process_view(garment, "front", storage)
        if back is not None:
            process_view(garment, "back", storage)
        db.commit()
        db.refresh(garment)
        return GarmentResponse.from_model(garment)
    except HTTPException:
        db.rollback()
        shutil.rmtree(storage.root / "garments" / garment_id, ignore_errors=True)
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(422, str(exc)) from exc


@router.post("/{garment_id}/process", response_model=GarmentResponse)
def process_garment(
    garment_id: str,
    db: Session = Depends(get_db),
    storage: LocalStorage = Depends(get_storage),
) -> GarmentResponse:
    garment = require_garment(db, garment_id)
    errors: list[str] = []
    for view in ("front", "back"):
        if not getattr(garment, f"raw_{view}_path"):
            continue
        try:
            process_view(garment, view, storage)
        except Exception as exc:
            errors.append(f"{view}: {exc}")
    db.commit()
    db.refresh(garment)
    if len(errors) == 2:
        raise HTTPException(422, "; ".join(errors))
    return GarmentResponse.from_model(garment)


@router.patch("/{garment_id}/images", response_model=GarmentResponse)
async def replace_garment_images(
    garment_id: str,
    front: UploadFile | None = File(default=None),
    back: UploadFile | None = File(default=None),
    db: Session = Depends(get_db),
    storage: LocalStorage = Depends(get_storage),
) -> GarmentResponse:
    if front is None and back is None:
        raise HTTPException(422, "Upload at least one replacement garment image.")
    garment = require_garment(db, garment_id)
    next_version = garment.garment_version + 1
    try:
        for view, upload in (("front", front), ("back", back)):
            if upload is None:
                continue
            setattr(
                garment,
                f"raw_{view}_path",
                await storage.save_upload(upload, Path("garments") / garment_id / f"raw_{view}_v{next_version}"),
            )
            setattr(garment, f"{view}_image_version", getattr(garment, f"{view}_image_version") + 1)
            setattr(garment, f"{view}_status", GenerationStatus.NOT_GENERATED)
            setattr(garment, f"{view}_error", None)
            process_view(garment, view, storage)
        garment.garment_version = next_version
        db.commit()
        db.refresh(garment)
        return GarmentResponse.from_model(garment)
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(422, f"Replacement image could not be processed: {exc}") from exc


def queue_views(
    garment: Garment,
    views: tuple[Literal["front", "back"], ...],
    db: Session,
    storage: LocalStorage,
    manager: GenerationManager,
) -> GenerationResponse:
    app_settings = get_or_create_settings(db)
    queued: list[str] = []
    cached: list[str] = []
    for view in views:
        if is_cache_valid(garment, app_settings, view, storage, manager.settings):
            setattr(garment, f"{view}_status", GenerationStatus.READY)
            cached.append(view)
            continue
        if not getattr(app_settings, f"body_{view}_path"):
            setattr(garment, f"{view}_status", GenerationStatus.FAILED)
            setattr(garment, f"{view}_error", f"Upload the {view} body reference first.")
            continue
        if not getattr(garment, f"clean_{view}_path"):
            setattr(garment, f"{view}_status", GenerationStatus.NOT_GENERATED)
            setattr(garment, f"{view}_error", f"Add a {view} garment photo to generate this view.")
            continue
        setattr(garment, f"{view}_status", GenerationStatus.PROCESSING)
        setattr(garment, f"{view}_error", None)
        if manager.queue(garment.id, view):
            queued.append(view)
    db.commit()
    db.refresh(garment)
    return GenerationResponse(
        garment=GarmentResponse.from_model(
            garment,
            manager.progress_for(garment.id),
            manager.stages_for(garment.id),
        ),
        queued_views=queued,
        cached_views=cached,
    )


@router.post("/{garment_id}/generate", response_model=GenerationResponse, status_code=status.HTTP_202_ACCEPTED)
def generate_both(
    garment_id: str,
    db: Session = Depends(get_db),
    storage: LocalStorage = Depends(get_storage),
    manager: GenerationManager = Depends(get_generation_manager),
) -> GenerationResponse:
    return queue_views(require_garment(db, garment_id), ("front", "back"), db, storage, manager)


@router.post("/{garment_id}/generate/{view}", response_model=GenerationResponse, status_code=status.HTTP_202_ACCEPTED)
def generate_view(
    garment_id: str,
    view: Literal["front", "back"],
    db: Session = Depends(get_db),
    storage: LocalStorage = Depends(get_storage),
    manager: GenerationManager = Depends(get_generation_manager),
) -> GenerationResponse:
    return queue_views(require_garment(db, garment_id), (view,), db, storage, manager)


@router.get("/{garment_id}/tryon/{view}")
def get_tryon(
    garment_id: str,
    view: Literal["front", "back"],
    db: Session = Depends(get_db),
    storage: LocalStorage = Depends(get_storage),
) -> Response:
    garment = require_garment(db, garment_id)
    app_settings = get_or_create_settings(db)
    if not is_cache_valid(garment, app_settings, view, storage, get_settings()):
        raise HTTPException(404, "A current cached try-on is not available for this view.")
    path = storage.resolve(getattr(garment, f"tryon_{view}_path"))
    from fastapi.responses import FileResponse
    return FileResponse(path, media_type="image/png", headers={"Cache-Control": "private, max-age=31536000, immutable"})


@router.delete("/{garment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_garment(
    garment_id: str,
    db: Session = Depends(get_db),
    storage: LocalStorage = Depends(get_storage),
) -> Response:
    garment = require_garment(db, garment_id)
    directory = storage.garment_dir(garment.id)
    db.delete(garment)
    db.commit()
    if directory.is_dir() and directory.parent == (storage.root / "garments").resolve():
        shutil.rmtree(directory)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
