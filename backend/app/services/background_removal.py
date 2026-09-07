from __future__ import annotations

import logging
from pathlib import Path
from threading import Lock

from PIL import Image, ImageOps


logger = logging.getLogger(__name__)


class BackgroundRemovalUnavailable(RuntimeError):
    pass


class BackgroundRemovalService:
    def __init__(self, model_name: str = "birefnet-general") -> None:
        self.model_name = model_name
        self._session = None
        self._lock = Lock()

    @property
    def available(self) -> bool:
        try:
            import rembg  # noqa: F401
            return True
        except ImportError:
            return False

    def remove(self, input_path: Path, output_path: Path) -> Path:
        try:
            from rembg import new_session, remove
        except ImportError as exc:
            raise BackgroundRemovalUnavailable(
                "Background removal is unavailable. Install backend requirements, including rembg."
            ) from exc

        with Image.open(input_path) as source:
            oriented = ImageOps.exif_transpose(source).convert("RGBA")
            alpha_min, alpha_max = oriented.getchannel("A").getextrema()
            if alpha_min == 0 and alpha_max == 255:
                logger.info("Keeping existing transparency for %s", input_path.name)
                result = oriented
            else:
                with self._lock:
                    if self._session is None:
                        logger.info("Loading rembg segmentation model '%s'", self.model_name)
                        try:
                            self._session = new_session(self.model_name)
                        except Exception as exc:
                            raise BackgroundRemovalUnavailable(
                                f"Could not load rembg model '{self.model_name}': {exc}"
                            ) from exc
                    result = remove(oriented, session=self._session)
            if not isinstance(result, Image.Image):
                raise RuntimeError("rembg returned an unexpected result type.")
            output_path.parent.mkdir(parents=True, exist_ok=True)
            # This is an intermediate file deleted after normalization. Spending
            # seconds on maximum PNG compression only slows every upload.
            result.convert("RGBA").save(output_path, "PNG", compress_level=1)
        return output_path


_service: BackgroundRemovalService | None = None


def get_background_removal_service(model_name: str) -> BackgroundRemovalService:
    global _service
    if _service is None or _service.model_name != model_name:
        _service = BackgroundRemovalService(model_name)
    return _service
