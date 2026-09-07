from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Lock

from sqlalchemy import select

from app.config import Settings
from app.database import session_scope
from app.models import AppSettings, Garment, GenerationStatus
from app.services.catvton_service import get_vton_service
from app.services.body_processor import BodyProcessor
from app.services.storage import LocalStorage


logger = logging.getLogger(__name__)


class GenerationManager:
    def __init__(self, settings: Settings, storage: LocalStorage) -> None:
        self.settings = settings
        self.storage = storage
        self.executor = ThreadPoolExecutor(max_workers=settings.generation_workers, thread_name_prefix="vton")
        self._active: set[tuple[str, str]] = set()
        self._progress: dict[tuple[str, str], int] = {}
        self._stages: dict[tuple[str, str], str] = {}
        self._lock = Lock()

    def queue(self, garment_id: str, view: str) -> bool:
        key = (garment_id, view)
        with self._lock:
            if key in self._active:
                return False
            self._active.add(key)
            self._progress[key] = 1
            self._stages[key] = "Queued"
        self.executor.submit(self._run, garment_id, view)
        return True

    def progress_for(self, garment_id: str) -> dict[str, int]:
        with self._lock:
            return {
                view: progress
                for (active_garment_id, view), progress in self._progress.items()
                if active_garment_id == garment_id
            }

    def stages_for(self, garment_id: str) -> dict[str, str]:
        with self._lock:
            return {
                view: stage
                for (active_garment_id, view), stage in self._stages.items()
                if active_garment_id == garment_id
            }

    def _report_progress(self, garment_id: str, view: str, percent: int, _stage: str) -> None:
        with self._lock:
            key = (garment_id, view)
            if key in self._active:
                self._progress[key] = max(1, min(100, percent))
                self._stages[key] = _stage

    def shutdown(self) -> None:
        self.executor.shutdown(wait=False, cancel_futures=False)

    def _run(self, garment_id: str, view: str) -> None:
        try:
            with session_scope() as session:
                garment = session.get(Garment, garment_id)
                app_settings = session.scalar(select(AppSettings).limit(1))
                if garment is None or app_settings is None:
                    return
                person_relative = getattr(app_settings, f"body_{view}_path")
                garment_relative = getattr(garment, f"clean_{view}_path")
                if not person_relative:
                    raise RuntimeError(f"Upload the {view} body reference before generation.")
                if not garment_relative:
                    raise RuntimeError(f"The {view} garment image has not been processed.")
                category = garment.category
                image_version = getattr(garment, f"{view}_image_version")
                body_version = app_settings.body_reference_version
                destination = self.storage.garment_dir(garment.id) / f"tryon_{view}.png"

            # Do not keep a SQLite transaction open during expensive inference.
            service = get_vton_service(self.settings)
            service.generate(
                str(self.storage.resolve(person_relative)),
                str(self.storage.resolve(garment_relative)),
                category,
                str(destination),
                lambda percent, stage: self._report_progress(garment_id, view, percent, stage),
            )
            self._report_progress(garment_id, view, 96, "Preparing player cutout")
            cutout_relative = BodyProcessor(self.settings, self.storage).create_display_cutout(
                self.storage.relative(destination),
                f"garments/{garment_id}/tryon_{view}_cutout.png",
            )
            with session_scope() as session:
                garment = session.get(Garment, garment_id)
                if garment is None:
                    return
                current_settings = session.scalar(select(AppSettings).limit(1))
                if (
                    current_settings is None
                    or getattr(garment, f"{view}_image_version") != image_version
                    or current_settings.body_reference_version != body_version
                ):
                    setattr(garment, f"{view}_status", GenerationStatus.NOT_GENERATED)
                    setattr(garment, f"{view}_error", "Inputs changed during generation; generate this view again.")
                    logger.info("Discarded stale generation: garment=%s view=%s", garment_id, view)
                    return
                setattr(garment, f"tryon_{view}_path", self.storage.relative(destination))
                setattr(garment, f"tryon_{view}_cutout_path", cutout_relative)
                setattr(garment, f"tryon_{view}_garment_version", image_version)
                setattr(garment, f"tryon_{view}_body_version", body_version)
                setattr(garment, f"tryon_{view}_profile", self.settings.vton_profile_key)
                setattr(garment, f"{view}_status", GenerationStatus.READY)
                logger.info("Generation ready: garment=%s view=%s", garment_id, view)
        except Exception as exc:
            logger.exception("Generation failed: garment=%s view=%s", garment_id, view)
            with session_scope() as session:
                garment = session.get(Garment, garment_id)
                if garment:
                    setattr(garment, f"{view}_status", GenerationStatus.FAILED)
                    setattr(garment, f"{view}_error", str(exc)[:1000])
        finally:
            with self._lock:
                self._active.discard((garment_id, view))
                self._progress.pop((garment_id, view), None)
                self._stages.pop((garment_id, view), None)


def is_cache_valid(
    garment: Garment,
    app_settings: AppSettings,
    view: str,
    storage: LocalStorage,
    settings: Settings,
) -> bool:
    relative = getattr(garment, f"tryon_{view}_path")
    return bool(
        relative
        and storage.resolve(relative).is_file()
        and getattr(garment, f"tryon_{view}_garment_version") == getattr(garment, f"{view}_image_version")
        and getattr(garment, f"tryon_{view}_body_version") == app_settings.body_reference_version
        and getattr(garment, f"tryon_{view}_profile") == settings.vton_profile_key
    )


def recover_interrupted_jobs(settings: Settings) -> None:
    """A local process restart cannot resume in-memory work, so make those views retryable."""
    with session_scope() as session:
        garments = session.scalars(
            select(Garment).where(
                (Garment.front_status == GenerationStatus.PROCESSING)
                | (Garment.back_status == GenerationStatus.PROCESSING)
            )
        ).all()
        for garment in garments:
            if garment.front_status == GenerationStatus.PROCESSING:
                garment.front_status = GenerationStatus.NOT_GENERATED
                garment.front_error = "Generation was interrupted by an application restart."
            if garment.back_status == GenerationStatus.PROCESSING:
                garment.back_status = GenerationStatus.NOT_GENERATED
                garment.back_error = "Generation was interrupted by an application restart."
        ready_garments = session.scalars(
            select(Garment).where(
                (Garment.front_status == GenerationStatus.READY)
                | (Garment.back_status == GenerationStatus.READY)
            )
        ).all()
        for garment in ready_garments:
            for view in ("front", "back"):
                if (
                    getattr(garment, f"{view}_status") == GenerationStatus.READY
                    and getattr(garment, f"tryon_{view}_profile") != settings.vton_profile_key
                ):
                    setattr(garment, f"{view}_status", GenerationStatus.NOT_GENERATED)
                    setattr(garment, f"{view}_error", None)
