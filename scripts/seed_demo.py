from __future__ import annotations

import argparse
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.config import get_settings  # noqa: E402
from app.database import create_database, session_scope  # noqa: E402
from app.models import AppSettings, Garment, GenerationStatus  # noqa: E402
from app.services.image_normalizer import ImageNormalizer  # noqa: E402
from app.services.body_processor import BodyProcessor  # noqa: E402
from app.services.storage import LocalStorage  # noqa: E402


@dataclass(frozen=True)
class DemoGarment:
    id: str
    name: str
    category: str
    color: str
    asset_name: str


DEMO_GARMENTS = (
    DemoGarment("00000000-0000-4000-8000-000000000101", "Essential Black Tee", "T-Shirt", "Black", "black_tee.png"),
    DemoGarment("00000000-0000-4000-8000-000000000102", "Ivory Studio Shirt", "Shirt", "Ivory", "ivory_shirt.png"),
    DemoGarment("00000000-0000-4000-8000-000000000103", "Indigo Straight Jeans", "Jeans", "Indigo", "blue_jeans.png"),
    DemoGarment("00000000-0000-4000-8000-000000000104", "Charcoal Tailored Trousers", "Pants", "Charcoal", "charcoal_trousers.png"),
)


def copy_atomic(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".seeding")
    shutil.copy2(source, temporary)
    temporary.replace(destination)


def main() -> None:
    parser = argparse.ArgumentParser(description="Add the bundled placeholder body and four demo garments.")
    parser.add_argument(
        "--replace-body",
        action="store_true",
        help="Replace an existing body reference. By default, a real user upload is preserved.",
    )
    args = parser.parse_args()

    settings = get_settings()
    storage = LocalStorage(settings)
    storage.initialize()
    create_database()
    assets = PROJECT_ROOT / "assets" / "seed"
    required = [assets / "body_reference.png", *(assets / item.asset_name for item in DEMO_GARMENTS)]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise SystemExit(f"Missing bundled demo assets: {', '.join(missing)}")

    normalizer = ImageNormalizer(settings.normalized_canvas_size)
    with session_scope() as session:
        app_settings = session.scalar(select(AppSettings).limit(1))
        if app_settings is None:
            app_settings = AppSettings(id=1)
            session.add(app_settings)
            session.flush()

        if args.replace_body or not (app_settings.body_front_path and app_settings.body_back_path):
            front_body = storage.root / "user" / "me_front.png"
            back_body = storage.root / "user" / "me_back.png"
            copy_atomic(assets / "body_reference.png", front_body)
            copy_atomic(assets / "body_reference.png", back_body)
            app_settings.body_front_path = storage.relative(front_body)
            app_settings.body_back_path = storage.relative(back_body)
            body_processor = BodyProcessor(settings, storage)
            app_settings.body_front_cutout_path = body_processor.create_cutout(app_settings.body_front_path, "front")
            app_settings.body_back_cutout_path = body_processor.create_cutout(app_settings.body_back_path, "back")
            app_settings.body_reference_version += 1
            print("Seeded one placeholder body image for both front and back views.")
        else:
            print("Kept the existing body reference. Use --replace-body to overwrite it.")

        for item in DEMO_GARMENTS:
            garment = session.get(Garment, item.id)
            if garment is not None:
                print(f"Kept existing demo garment: {item.name}")
                continue

            directory = storage.garment_dir(item.id)
            raw_front = directory / "raw_front.png"
            raw_back = directory / "raw_back.png"
            clean_front = directory / "clean_front.png"
            clean_back = directory / "clean_back.png"
            source = assets / item.asset_name
            copy_atomic(source, raw_front)
            copy_atomic(source, raw_back)
            normalizer.normalize(raw_front, clean_front)
            normalizer.normalize(raw_back, clean_back)
            session.add(
                Garment(
                    id=item.id,
                    name=item.name,
                    brand="Digital Wardrobe Demo",
                    category=item.category,
                    color=item.color,
                    raw_front_path=storage.relative(raw_front),
                    raw_back_path=storage.relative(raw_back),
                    clean_front_path=storage.relative(clean_front),
                    clean_back_path=storage.relative(clean_back),
                    front_status=GenerationStatus.NOT_GENERATED,
                    back_status=GenerationStatus.NOT_GENERATED,
                )
            )
            print(f"Seeded demo garment: {item.name}")

    print(f"Demo wardrobe ready at {settings.data_dir}")


if __name__ == "__main__":
    main()
