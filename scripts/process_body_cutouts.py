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
from app.models import AppSettings  # noqa: E402
from app.services.body_processor import BodyProcessor  # noqa: E402
from app.services.storage import LocalStorage  # noqa: E402


def main() -> None:
    settings = get_settings()
    storage = LocalStorage(settings)
    storage.initialize()
    create_database()
    processor = BodyProcessor(settings, storage)
    processed = 0
    for view in ("front", "back"):
        with session_scope() as session:
            app_settings = session.scalar(select(AppSettings).limit(1))
            if app_settings is None:
                raise SystemExit("No profile exists yet. Upload a front body image first.")
            source = getattr(app_settings, f"body_{view}_path")
            if not source:
                continue
            existing = storage.root / "user" / f"me_{view}_cutout.png"
            cutout = processor.trim_transparent(storage.relative(existing)) if existing.is_file() else processor.create_cutout(source, view)
            setattr(app_settings, f"body_{view}_cutout_path", cutout)
            processed += int(bool(cutout))
    print(f"Prepared {processed} transparent body view(s).")


if __name__ == "__main__":
    main()
