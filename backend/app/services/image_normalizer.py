from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
from PIL import Image


class ImageQualityError(ValueError):
    pass


@dataclass(frozen=True)
class NormalizationReport:
    source_width: int
    source_height: int
    foreground_ratio: float
    rotation_degrees: float


class ImageNormalizer:
    def __init__(self, canvas_size: int = 1024, padding_ratio: float = 0.08) -> None:
        self.canvas_size = canvas_size
        self.padding_ratio = padding_ratio

    def normalize(self, input_path: Path, output_path: Path) -> NormalizationReport:
        with Image.open(input_path) as loaded:
            image = loaded.convert("RGBA")
        width, height = image.size
        if min(width, height) < 256:
            raise ImageQualityError("Image is extremely low resolution; use an image at least 256 px on each side.")

        alpha = np.asarray(image.getchannel("A"))
        mask = alpha > 12
        foreground_ratio = float(mask.mean())
        if foreground_ratio < 0.01:
            raise ImageQualityError("Segmentation mask contains almost nothing. Try a clearer garment photo.")
        if not mask.any():
            raise ImageQualityError("The resulting alpha channel is empty.")
        border_hits = [mask[0].any(), mask[-1].any(), mask[:, 0].any(), mask[:, -1].any()]
        if all(border_hits):
            raise ImageQualityError("The garment touches every image border. Retake the photo with space around it.")

        image, rotation = self._safely_deskew(image)
        alpha = np.asarray(image.getchannel("A"))
        points = cv2.findNonZero((alpha > 12).astype(np.uint8))
        if points is None:
            raise ImageQualityError("The resulting alpha channel is empty.")
        x, y, box_width, box_height = cv2.boundingRect(points)
        pad = round(max(box_width, box_height) * self.padding_ratio)
        left = max(0, x - pad)
        top = max(0, y - pad)
        right = min(image.width, x + box_width + pad)
        bottom = min(image.height, y + box_height + pad)
        cropped = image.crop((left, top, right, bottom))

        max_content = round(self.canvas_size * 0.86)
        scale = min(max_content / cropped.width, max_content / cropped.height, 1.0)
        resized = cropped.resize(
            (max(1, round(cropped.width * scale)), max(1, round(cropped.height * scale))),
            Image.Resampling.LANCZOS,
        )
        canvas = Image.new("RGBA", (self.canvas_size, self.canvas_size), (0, 0, 0, 0))
        offset = ((self.canvas_size - resized.width) // 2, (self.canvas_size - resized.height) // 2)
        canvas.alpha_composite(resized, offset)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        canvas.save(output_path, "PNG", compress_level=1)
        return NormalizationReport(width, height, foreground_ratio, rotation)

    @staticmethod
    def _safely_deskew(image: Image.Image) -> tuple[Image.Image, float]:
        alpha = np.asarray(image.getchannel("A"))
        coordinates = np.column_stack(np.nonzero(alpha > 32))
        if len(coordinates) < 100:
            return image, 0.0
        sample = coordinates[:: max(1, len(coordinates) // 25_000)]
        centered = sample - sample.mean(axis=0)
        covariance = np.cov(centered, rowvar=False)
        values, vectors = np.linalg.eigh(covariance)
        axis = vectors[:, np.argmax(values)]
        angle = float(np.degrees(np.arctan2(axis[1], axis[0])))
        correction = ((90.0 - angle + 90.0) % 180.0) - 90.0
        if 2.0 <= abs(correction) <= 10.0:
            return image.rotate(correction, resample=Image.Resampling.BICUBIC, expand=True), correction
        return image, 0.0
