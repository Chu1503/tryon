from __future__ import annotations

from pathlib import Path
from typing import Protocol


class WrinkleCleaner(Protocol):
    def clean(self, image_path: str) -> str:
        """Return the path to a cleaned image without changing garment identity."""


class NoOpWrinkleCleaner:
    """V1 intentionally preserves the normalized garment without generative edits."""

    def clean(self, image_path: str) -> str:
        if not Path(image_path).is_file():
            raise FileNotFoundError(image_path)
        return image_path


def get_wrinkle_cleaner(_enabled: bool) -> WrinkleCleaner:
    # A future identity-preserving implementation can be selected here.
    return NoOpWrinkleCleaner()
