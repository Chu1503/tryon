from __future__ import annotations

import logging
from pathlib import Path

from app.config import Settings
from app.services.background_removal import get_background_removal_service
from app.services.image_normalizer import ImageNormalizer, NormalizationReport
from app.services.wrinkle_cleaner import get_wrinkle_cleaner


logger = logging.getLogger(__name__)


class GarmentProcessor:
    def __init__(self, settings: Settings) -> None:
        self.background_removal = get_background_removal_service(settings.rembg_model)
        self.normalizer = ImageNormalizer(settings.normalized_canvas_size)
        self.wrinkle_cleaner = get_wrinkle_cleaner(settings.enable_wrinkle_cleaning)

    def process(self, raw_path: Path, clean_path: Path) -> NormalizationReport:
        segmented_path = clean_path.with_name(f".{clean_path.stem}_segmented.png")
        try:
            self.background_removal.remove(raw_path, segmented_path)
            report = self.normalizer.normalize(segmented_path, clean_path)
            result = self.wrinkle_cleaner.clean(str(clean_path))
            if Path(result).resolve() != clean_path.resolve():
                raise RuntimeError("Wrinkle cleaner must return the configured normalized output path.")
            logger.info("Processed garment %s -> %s", raw_path.name, clean_path.name)
            return report
        finally:
            segmented_path.unlink(missing_ok=True)
