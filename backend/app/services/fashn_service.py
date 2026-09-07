from __future__ import annotations

import logging
import time
from pathlib import Path
from threading import Lock
from typing import Callable

from PIL import Image

from app.config import Settings


logger = logging.getLogger(__name__)

FASHN_CATEGORY_MAP = {
    "T-Shirt": "tops",
    "Polo": "tops",
    "Shirt": "tops",
    "Sweater": "tops",
    "Hoodie": "tops",
    "Jacket": "tops",
    "Pants": "bottoms",
    "Sweatpants": "bottoms",
    "Jeans": "bottoms",
    "Shorts": "bottoms",
    "Other": "one-pieces",
}


class FashnHuggingFaceService:
    """Adapter for the official FASHN VTON v1.5 Hugging Face Space."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._client = None
        self._client_lock = Lock()

    @property
    def token_configured(self) -> bool:
        return bool(self.settings.hf_token and self.settings.hf_token.strip())

    def _get_client(self):  # type: ignore[no-untyped-def]
        if self._client is not None:
            return self._client
        with self._client_lock:
            if self._client is None:
                try:
                    from gradio_client import Client
                except ImportError as exc:
                    raise RuntimeError(
                        "Online FASHN support is not installed. Run pip install -r backend/requirements.txt."
                    ) from exc
                logger.info("Connecting to FASHN Space '%s'", self.settings.fashn_space)
                self._client = Client(
                    self.settings.fashn_space,
                    token=self.settings.hf_token.strip() if self.token_configured else None,
                    verbose=False,
                )
        return self._client

    def generate(
        self,
        person_image: str,
        garment_image: str,
        garment_category: str,
        output_path: str,
        progress_callback: Callable[[int, str], None] | None = None,
    ) -> str:
        try:
            from gradio_client import handle_file
        except ImportError as exc:
            raise RuntimeError("gradio_client is required for online FASHN generation.") from exc

        if progress_callback:
            progress_callback(3, "Connecting to FASHN ZeroGPU")
        client = self._get_client()
        category = FASHN_CATEGORY_MAP.get(garment_category, "one-pieces")
        logger.info(
            "Submitting FASHN VTON: space=%s category=%s steps=%s authenticated=%s",
            self.settings.fashn_space,
            category,
            self.settings.fashn_steps,
            self.token_configured,
        )
        job = client.submit(
            person_image=handle_file(person_image),
            garment_image=handle_file(garment_image),
            category=category,
            garment_photo_type="flat-lay",
            num_timesteps=self.settings.fashn_steps,
            guidance_scale=self.settings.fashn_guidance_scale,
            seed=42,
            segmentation_free=True,
            api_name="/try_on",
        )

        started = time.monotonic()
        while not job.done():
            status = job.status()
            code = str(getattr(status, "code", "")).lower()
            rank = getattr(status, "rank", None)
            if "queue" in code:
                detail = f"Waiting for free GPU · queue {rank + 1}" if isinstance(rank, int) else "Waiting for free GPU"
                percent = 8
            else:
                elapsed = time.monotonic() - started
                percent = min(92, 15 + round(elapsed * 1.4))
                detail = "Generating with FASHN VTON"
            if progress_callback:
                progress_callback(percent, detail)
            time.sleep(1)

        if progress_callback:
            progress_callback(95, "Downloading high-quality result")
        result = job.result()
        if isinstance(result, (tuple, list)):
            result = result[0]
        if isinstance(result, dict):
            result = result.get("path") or result.get("url")
        if not isinstance(result, str):
            raise RuntimeError("FASHN returned an unexpected result.")

        destination = Path(output_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with Image.open(result) as image:
            image.convert("RGB").save(destination, "PNG", compress_level=1)
        if progress_callback:
            progress_callback(100, "Ready")
        return str(destination)
