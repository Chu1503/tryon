from __future__ import annotations

import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Callable, Protocol

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from app.config import Settings


logger = logging.getLogger(__name__)


CATEGORY_MAP = {
    "T-Shirt": "upper", "Polo": "upper", "Shirt": "upper", "Sweater": "upper", "Hoodie": "upper", "Jacket": "upper",
    "Pants": "lower", "Jeans": "lower", "Shorts": "lower", "Sweatpants": "lower", "Other": "overall",
}


class VirtualTryOnUnavailable(RuntimeError):
    pass


class VirtualTryOnService(Protocol):
    def generate(
        self,
        person_image: str,
        garment_image: str,
        garment_category: str,
        output_path: str,
        progress_callback: Callable[[int, str], None] | None = None,
    ) -> str:
        ...


@dataclass(frozen=True)
class VtonCapability:
    mode: str
    available: bool
    device: str | None
    detail: str


class MockVirtualTryOnService:
    """Fast visual placeholder used only when MOCK_VTON=true."""

    def generate(
        self,
        person_image: str,
        garment_image: str,
        garment_category: str,
        output_path: str,
        progress_callback: Callable[[int, str], None] | None = None,
    ) -> str:
        if progress_callback:
            progress_callback(20, "Preparing preview")
        with Image.open(person_image) as source:
            person = source.convert("RGB")
        with Image.open(garment_image) as source:
            garment = source.convert("RGBA")
        target_width = round(person.width * (0.58 if CATEGORY_MAP.get(garment_category) == "upper" else 0.62))
        target_height = round(person.height * (0.44 if CATEGORY_MAP.get(garment_category) == "upper" else 0.48))
        garment.thumbnail((target_width, target_height), Image.Resampling.LANCZOS)
        overlay = person.convert("RGBA")
        y_ratio = 0.25 if CATEGORY_MAP.get(garment_category) == "upper" else 0.49
        position = ((person.width - garment.width) // 2, round(person.height * y_ratio))
        overlay.alpha_composite(garment, position)
        draw = ImageDraw.Draw(overlay)
        label = "MOCK VTON · configure CatVTON for AI output"
        box = draw.textbbox((0, 0), label, font=ImageFont.load_default())
        x = (person.width - (box[2] - box[0])) // 2
        draw.rounded_rectangle((x - 10, 14, x + box[2] - box[0] + 10, 42), radius=8, fill=(22, 22, 20, 205))
        draw.text((x, 23), label, fill=(255, 255, 255, 255), font=ImageFont.load_default())
        destination = Path(output_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        overlay.convert("RGB").save(destination, "PNG", compress_level=1)
        if progress_callback:
            progress_callback(100, "Ready")
        return str(destination)


class CatVTONService:
    """Lazy adapter around the official Zheng-Chong/CatVTON implementation."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._load_lock = Lock()
        self._inference_lock = Lock()
        self._pipeline = None
        self._automasker = None
        self._mask_processor = None
        self._resize_and_crop = None
        self._resize_and_padding = None
        self._repaint_result = None
        self._torch = None
        self._device: str | None = None

    def capability(self) -> VtonCapability:
        if not (self.settings.catvton_repo_path / "model" / "pipeline.py").is_file():
            return VtonCapability("catvton", False, None, "Official CatVTON repository is not installed.")
        try:
            import torch
        except ImportError:
            return VtonCapability("catvton", False, None, "PyTorch is not installed in this environment.")
        if torch.cuda.is_available():
            return VtonCapability("catvton", True, "cuda", f"CUDA GPU: {torch.cuda.get_device_name(0)}")
        if self.settings.catvton_allow_cpu:
            return VtonCapability("catvton", True, "cpu", "CPU enabled; inference will be very slow.")
        return VtonCapability("catvton", False, "cpu", "CUDA is unavailable and CATVTON_ALLOW_CPU is false.")

    def _load(self) -> None:
        if self._pipeline is not None:
            return
        with self._load_lock:
            if self._pipeline is not None:
                return
            capability = self.capability()
            if not capability.available:
                raise VirtualTryOnUnavailable(capability.detail)
            repo = str(self.settings.catvton_repo_path.resolve())
            if repo not in sys.path:
                # Keep site-packages ahead of the bundled Python 3.9 Detectron2
                # binary. The WSL environment installs a Python 3.10 build.
                sys.path.append(repo)
            # Detectron2 0.6 references the Pillow 9 alias removed in Pillow 10.
            if not hasattr(Image, "LINEAR"):
                Image.LINEAR = Image.Resampling.BILINEAR  # type: ignore[attr-defined]
            try:
                import torch
                from diffusers.image_processor import VaeImageProcessor
                from huggingface_hub import snapshot_download
                from model.cloth_masker import AutoMasker
                from model.pipeline import CatVTONPipeline
                from utils import init_weight_dtype, repaint_result, resize_and_crop, resize_and_padding
            except Exception as exc:
                raise VirtualTryOnUnavailable(f"CatVTON dependencies could not be imported: {exc}") from exc

            device = "cuda" if torch.cuda.is_available() else "cpu"
            precision = self.settings.catvton_precision if device == "cuda" else "no"
            logger.info("Loading CatVTON once on %s with %s precision", device, precision)
            checkpoint_path = snapshot_download(repo_id=self.settings.catvton_checkpoint)
            self._pipeline = CatVTONPipeline(
                base_ckpt=self.settings.catvton_base_model,
                attn_ckpt=checkpoint_path,
                attn_ckpt_version="mix",
                weight_dtype=init_weight_dtype(precision),
                use_tf32=device == "cuda",
                skip_safety_check=self.settings.catvton_skip_safety_check,
                device=device,
            )
            self._automasker = AutoMasker(
                densepose_ckpt=str(Path(checkpoint_path) / "DensePose"),
                schp_ckpt=str(Path(checkpoint_path) / "SCHP"),
                device=device,
            )
            self._mask_processor = VaeImageProcessor(
                vae_scale_factor=8, do_normalize=False, do_binarize=True, do_convert_grayscale=True
            )
            self._resize_and_crop = resize_and_crop
            self._resize_and_padding = resize_and_padding
            self._repaint_result = repaint_result
            self._torch = torch
            self._device = device

    def generate(
        self,
        person_image: str,
        garment_image: str,
        garment_category: str,
        output_path: str,
        progress_callback: Callable[[int, str], None] | None = None,
    ) -> str:
        if progress_callback:
            progress_callback(3, "Loading CatVTON")
        self._load()
        assert self._pipeline and self._automasker and self._mask_processor
        assert self._resize_and_padding and self._repaint_result and self._torch and self._device
        with self._inference_lock:
            if progress_callback:
                progress_callback(15, "Preparing person and garment")
            with Image.open(person_image) as image:
                target_size = (self.settings.catvton_width, self.settings.catvton_height)
                # CatVTON's demo center-crops to 3:4. Real phone/product photos
                # can be much narrower, which used to crop off the user's head
                # and feet. Contain the complete person on white instead.
                person = self._resize_and_padding(image.convert("RGB"), target_size)
            with Image.open(garment_image) as image:
                rgba = image.convert("RGBA")
                white = Image.new("RGBA", rgba.size, "white")
                white.alpha_composite(rgba)
                cloth = self._resize_and_padding(white.convert("RGB"), target_size)
            cloth_type = CATEGORY_MAP.get(garment_category, "overall")
            mask = self._automasker(person, cloth_type)["mask"]
            mask = self._mask_processor.blur(mask, blur_factor=9)
            if progress_callback:
                progress_callback(20, "Body mask ready")
            generator = self._torch.Generator(device=self._device).manual_seed(42)
            logger.info(
                "Running CatVTON: category=%s device=%s size=%sx%s steps=%s",
                cloth_type,
                self._device,
                self.settings.catvton_width,
                self.settings.catvton_height,
                self.settings.catvton_steps,
            )
            result = self._pipeline(
                image=person,
                condition_image=cloth,
                mask=mask,
                num_inference_steps=self.settings.catvton_steps,
                guidance_scale=self.settings.catvton_guidance_scale,
                width=self.settings.catvton_width,
                height=self.settings.catvton_height,
                generator=generator,
                callback_on_step_end=(
                    lambda completed, total: progress_callback(
                        20 + round(75 * completed / total),
                        f"Generating {completed}/{total}",
                    )
                    if progress_callback
                    else None
                ),
            )[0]
            # The official evaluation path repaints the untouched area from the
            # person image. This preserves face, body, hands and background
            # instead of letting diffusion alter the entire photograph.
            result = self._repaint_result(result, person, mask)
            if progress_callback:
                progress_callback(97, "Saving result")
            destination = Path(output_path)
            destination.parent.mkdir(parents=True, exist_ok=True)
            result.convert("RGB").save(destination, "PNG", compress_level=1)
            if progress_callback:
                progress_callback(100, "Ready")
            return str(destination)


class FallbackVirtualTryOnService:
    """Prefer hosted high quality, but retain unlimited local availability."""

    def __init__(self, primary: VirtualTryOnService, fallback: VirtualTryOnService) -> None:
        self.primary = primary
        self.fallback = fallback

    def generate(
        self,
        person_image: str,
        garment_image: str,
        garment_category: str,
        output_path: str,
        progress_callback: Callable[[int, str], None] | None = None,
    ) -> str:
        try:
            return self.primary.generate(
                person_image,
                garment_image,
                garment_category,
                output_path,
                progress_callback,
            )
        except Exception as exc:
            logger.warning("Hosted VTON unavailable; falling back to local CatVTON: %s", exc)
            if progress_callback:
                progress_callback(3, "Online quota unavailable · switching to local CatVTON")
            return self.fallback.generate(
                person_image,
                garment_image,
                garment_category,
                output_path,
                progress_callback,
            )


_service: VirtualTryOnService | None = None
_capability: VtonCapability | None = None
_service_init_lock = Lock()


def get_vton_service(settings: Settings) -> VirtualTryOnService:
    global _service, _capability
    if _service is None:
        with _service_init_lock:
            if _service is None:
                if settings.mock_vton:
                    capability = VtonCapability("mock", True, "cpu", "Mock compositor is enabled for development.")
                    service: VirtualTryOnService = MockVirtualTryOnService()
                else:
                    local_service = CatVTONService(settings)
                    local_capability = local_service.capability()
                    if settings.vton_provider.lower() in {"fashn", "fashn_hf", "hybrid"}:
                        from app.services.fashn_service import FashnHuggingFaceService

                        hosted_service = FashnHuggingFaceService(settings)
                        if settings.vton_provider.lower() == "hybrid":
                            service = FallbackVirtualTryOnService(hosted_service, local_service)
                            capability = VtonCapability(
                                "fashn-hf + catvton fallback",
                                True,
                                "cloud / cuda",
                                "FASHN VTON v1.5 ZeroGPU preferred; local CatVTON is used if quota or service is unavailable.",
                            )
                        else:
                            service = hosted_service
                            capability = VtonCapability(
                                "fashn-hf",
                                True,
                                "cloud",
                                "FASHN VTON v1.5 on Hugging Face ZeroGPU.",
                            )
                    else:
                        capability = local_capability
                        service = local_service
                # Publish capability first: readers that observe a service will
                # always observe its matching health status too.
                _capability = capability
                _service = service
    return _service


def get_vton_capability(settings: Settings) -> VtonCapability:
    get_vton_service(settings)
    assert _capability is not None
    return _capability
