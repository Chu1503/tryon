from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import select


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.config import get_settings  # noqa: E402
from app.database import create_database, session_scope  # noqa: E402
from app.models import Garment, GenerationStatus  # noqa: E402
from app.services.body_processor import BodyProcessor  # noqa: E402
from app.services.storage import LocalStorage  # noqa: E402


def main() -> None:
    settings = get_settings()
    storage = LocalStorage(settings)
    storage.initialize()
    create_database()
    processor = BodyProcessor(settings, storage)
    processed = 0
    with session_scope() as session:
        targets = [garment.id for garment in session.scalars(select(Garment)).all()]
    for garment_id in targets:
        for view in ("front", "back"):
            with session_scope() as session:
                garment = session.get(Garment, garment_id)
                if garment is None:
                    continue
                if getattr(garment, f"{view}_status") != GenerationStatus.READY:
                    continue
                source = getattr(garment, f"tryon_{view}_path")
                if not source or not storage.resolve(source).is_file():
                    continue
                destination = f"garments/{garment.id}/tryon_{view}_cutout.png"
                existing = storage.resolve(destination)
                cutout = processor.trim_transparent(storage.relative(existing)) if existing.is_file() else processor.create_display_cutout(source, destination)
                setattr(garment, f"tryon_{view}_cutout_path", cutout)
                processed += int(bool(cutout))
    print(f"Prepared {processed} cached try-on cutout(s).")


if __name__ == "__main__":
    main()
