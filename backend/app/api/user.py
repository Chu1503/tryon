from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.api.dependencies import get_db, get_storage
from app.models import AppSettings, Garment, GenerationStatus
from app.config import get_settings
from app.schemas.user import UserProfileUpdate, UserSettingsResponse
from app.services.body_processor import BodyProcessor
from app.services.storage import LocalStorage


router = APIRouter(prefix="/user", tags=["user"])
logger = logging.getLogger(__name__)


def get_or_create_settings(db: Session) -> AppSettings:
    settings = db.scalar(select(AppSettings).limit(1))
    if settings is None:
        settings = AppSettings(id=1)
        db.add(settings)
        db.flush()
    return settings


def to_response(settings: AppSettings) -> UserSettingsResponse:
    version = settings.body_reference_version
    return UserSettingsResponse(
        display_name=settings.display_name or "CHU",
        body_front_url=f"/api/assets/user/front?v={version}" if settings.body_front_path else None,
        body_back_url=f"/api/assets/user/back?v={version}" if settings.body_back_path else None,
        body_front_cutout_url=(
            f"/api/assets/user/front-cutout?v={version}" if settings.body_front_cutout_path else None
        ),
        body_back_cutout_url=(
            f"/api/assets/user/back-cutout?v={version}" if settings.body_back_cutout_path else None
        ),
        body_reference_version=version,
        is_complete=bool(settings.body_front_path),
    )


@router.get("", response_model=UserSettingsResponse)
def get_user(db: Session = Depends(get_db)) -> UserSettingsResponse:
    settings = get_or_create_settings(db)
    db.commit()
    return to_response(settings)


@router.patch("", response_model=UserSettingsResponse)
def update_user_profile(
    payload: UserProfileUpdate,
    db: Session = Depends(get_db),
) -> UserSettingsResponse:
    settings = get_or_create_settings(db)
    display_name = " ".join(payload.display_name.split()).strip()
    if not display_name:
        raise HTTPException(422, "Name is required.")
    settings.display_name = display_name[:80]
    db.commit()
    db.refresh(settings)
    return to_response(settings)


@router.post("/body-images", response_model=UserSettingsResponse)
async def upload_body_images(
    front: UploadFile | None = File(default=None),
    back: UploadFile | None = File(default=None),
    db: Session = Depends(get_db),
    storage: LocalStorage = Depends(get_storage),
) -> UserSettingsResponse:
    if front is None and back is None:
        raise HTTPException(422, "Upload at least one body reference image.")
    settings = get_or_create_settings(db)
    next_version = settings.body_reference_version + 1
    processor = BodyProcessor(get_settings(), storage)
    if front is not None:
        settings.body_front_path = await storage.save_upload(front, Path("user") / "me_front")
        settings.body_front_cutout_path = processor.create_cutout(settings.body_front_path, "front")
    if back is not None:
        settings.body_back_path = await storage.save_upload(back, Path("user") / "me_back")
        settings.body_back_cutout_path = processor.create_cutout(settings.body_back_path, "back")
    settings.body_reference_version = next_version
    db.execute(
        update(Garment).values(
            front_status=GenerationStatus.NOT_GENERATED,
            back_status=GenerationStatus.NOT_GENERATED,
            front_error=None,
            back_error=None,
        )
    )
    db.commit()
    db.refresh(settings)
    return to_response(settings)
