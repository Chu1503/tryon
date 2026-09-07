from __future__ import annotations

import io
from pathlib import Path

from fastapi import HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError

from app.config import Settings


SUPPORTED_FORMATS = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp"}


class LocalStorage:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.root = settings.data_dir.resolve()

    def initialize(self) -> None:
        (self.root / "user").mkdir(parents=True, exist_ok=True)
        (self.root / "garments").mkdir(parents=True, exist_ok=True)

    def garment_dir(self, garment_id: str) -> Path:
        target = (self.root / "garments" / garment_id).resolve()
        self._ensure_inside(target)
        target.mkdir(parents=True, exist_ok=True)
        return target

    async def save_upload(self, upload: UploadFile, relative_stem: Path) -> str:
        content = await upload.read(self.settings.max_upload_mb * 1024 * 1024 + 1)
        if len(content) > self.settings.max_upload_mb * 1024 * 1024:
            raise HTTPException(413, f"Image exceeds the {self.settings.max_upload_mb} MB upload limit.")
        try:
            with Image.open(io.BytesIO(content)) as image:
                image.verify()
                detected = image.format
        except (UnidentifiedImageError, OSError) as exc:
            raise HTTPException(422, "Upload is not a readable JPG, PNG, or WEBP image.") from exc
        if detected not in SUPPORTED_FORMATS:
            raise HTTPException(422, "Supported formats are JPG, JPEG, PNG, and WEBP.")
        destination = (self.root / relative_stem).with_suffix(SUPPORTED_FORMATS[detected]).resolve()
        self._ensure_inside(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix(destination.suffix + ".uploading")
        temporary.write_bytes(content)
        temporary.replace(destination)
        return destination.relative_to(self.root).as_posix()

    def resolve(self, relative_path: str) -> Path:
        path = (self.root / relative_path).resolve()
        self._ensure_inside(path)
        return path

    def relative(self, path: Path) -> str:
        resolved = path.resolve()
        self._ensure_inside(resolved)
        return resolved.relative_to(self.root).as_posix()

    def _ensure_inside(self, path: Path) -> None:
        if path != self.root and self.root not in path.parents:
            raise ValueError("Path escapes the configured data directory.")
