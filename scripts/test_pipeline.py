from __future__ import annotations

import argparse
import os
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.config import get_settings  # noqa: E402
from app.services.catvton_service import get_vton_service  # noqa: E402
from app.services.garment_processor import GarmentProcessor  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Run person + garment -> cached PNG pipeline.")
    parser.add_argument("--person", type=Path, required=True)
    parser.add_argument("--garment", type=Path, required=True)
    parser.add_argument("--category", default="T-Shirt")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--mock", action="store_true", help="Use mock VTON even if .env enables CatVTON.")
    args = parser.parse_args()
    for path in (args.person, args.garment):
        if not path.is_file():
            raise SystemExit(f"Input does not exist: {path}")
    if args.mock:
        os.environ["MOCK_VTON"] = "true"
        get_settings.cache_clear()
    settings = get_settings()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="digital-wardrobe-") as folder:
        cleaned = Path(folder) / "clean_garment.png"
        report = GarmentProcessor(settings).process(args.garment, cleaned)
        print(f"Normalized garment: foreground={report.foreground_ratio:.1%}, rotation={report.rotation_degrees:.1f}°")
        result = get_vton_service(settings).generate(str(args.person), str(cleaned), args.category, str(args.output))
    print(f"Try-on written to {result}")


if __name__ == "__main__":
    main()
