from __future__ import annotations

import logging
from pathlib import Path

from PIL import Image

from app.config import Settings
from app.services.background_removal import get_background_removal_service
from app.services.storage import LocalStorage


logger = logging.getLogger(__name__)


class BodyProcessor:
    """Create display-only transparent cutouts without changing VTON originals."""

    def __init__(self, settings: Settings, storage: LocalStorage) -> None:
        self.settings = settings
        self.storage = storage

    def create_cutout(self, source_relative: str, view: str) -> str | None:
        return self.create_display_cutout(source_relative, f"user/me_{view}_cutout.png")

    def create_display_cutout(self, source_relative: str, destination_relative: str) -> str | None:
        destination = self.storage.resolve(destination_relative)
        try:
            service = get_background_removal_service(self.settings.rembg_model)
            service.remove(self.storage.resolve(source_relative), destination)
            return self.trim_transparent(self.storage.relative(destination))
        except Exception:
            # The original is always retained and remains usable for VTON. A
            # missing optional cutout must never make profile upload fail.
            logger.exception("Could not create display cutout for %s", source_relative)
            return None

    def trim_transparent(self, relative_path: str) -> str:
        """Remove invisible canvas padding while keeping a small edge buffer."""
        path = self.storage.resolve(relative_path)
        with Image.open(path) as source:
            image = source.convert("RGBA")
            bounds = image.getchannel("A").getbbox()
            if bounds is None:
                raise ValueError("Display cutout has an empty alpha channel.")
            left, top, right, bottom = bounds
            padding = max(3, round(max(right - left, bottom - top) * 0.012))
            crop_box = (
                max(0, left - padding),
                max(0, top - padding),
                min(image.width, right + padding),
                min(image.height, bottom + padding),
            )
            cropped = image.crop(crop_box)
            temporary = path.with_suffix(".trim.png")
            cropped.save(temporary, "PNG", compress_level=2)
            temporary.replace(path)
        return self.storage.relative(path)
