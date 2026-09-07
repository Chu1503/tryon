from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_db, get_storage
from app.models import AppSettings, Garment
from app.services.storage import LocalStorage


router = APIRouter(prefix="/assets", tags=["assets"])


def safe_file(storage: LocalStorage, relative_path: str | None) -> FileResponse:
    if not relative_path:
        raise HTTPException(404, "Image is not available.")
    path = storage.resolve(relative_path)
    if not path.is_file():
        raise HTTPException(404, "Image file is missing.")
    media = "image/png" if path.suffix.lower() == ".png" else "image/webp" if path.suffix.lower() == ".webp" else "image/jpeg"
    return FileResponse(path, media_type=media, headers={"Cache-Control": "private, max-age=31536000, immutable"})


@router.get("/user/{view}")
def user_asset(
    view: str,
    db: Session = Depends(get_db),
    storage: LocalStorage = Depends(get_storage),
) -> FileResponse:
    if view not in {"front", "back", "front-cutout", "back-cutout"}:
        raise HTTPException(404, "Unknown body view.")
    settings = db.scalar(select(AppSettings).limit(1))
    field = f"body_{view.replace('-', '_')}_path"
    return safe_file(storage, getattr(settings, field, None) if settings else None)


@router.get("/garments/{garment_id}/{asset}")
def garment_asset(
    garment_id: str,
    asset: str,
    db: Session = Depends(get_db),
    storage: LocalStorage = Depends(get_storage),
) -> FileResponse:
    allowed = {
        "raw_front", "raw_back", "clean_front", "clean_back",
        "tryon_front_cutout", "tryon_back_cutout",
    }
    if asset not in allowed:
        raise HTTPException(404, "Unknown garment asset.")
    garment = db.get(Garment, garment_id)
    if garment is None:
        raise HTTPException(404, "Garment not found.")
    return safe_file(storage, getattr(garment, f"{asset}_path"))
