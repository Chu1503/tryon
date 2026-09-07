from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


REPOSITORY = "https://github.com/Zheng-Chong/CatVTON.git"


def main() -> None:
    parser = argparse.ArgumentParser(description="Install the official CatVTON source tree.")
    parser.add_argument("--destination", type=Path, default=Path(__file__).resolve().parents[1] / "models" / "CatVTON")
    parser.add_argument("--install-requirements", action="store_true", help="Install the tested CatVTON dependency set into the active Python environment.")
    args = parser.parse_args()
    destination = args.destination.resolve()
    if destination.exists():
        if not (destination / "model" / "pipeline.py").is_file():
            raise SystemExit(f"Destination exists but is not CatVTON: {destination}")
        print(f"CatVTON already exists at {destination}")
    else:
        destination.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "clone", "--depth", "1", REPOSITORY, str(destination)], check=True)
        print(f"Cloned official CatVTON into {destination}")
    if args.install_requirements:
        import sys
        requirements = Path(__file__).resolve().parents[1] / "backend" / "requirements-catvton-wsl.txt"
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", str(requirements)], check=True)
        subprocess.run(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "--no-build-isolation",
                "git+https://github.com/facebookresearch/detectron2.git@v0.6",
            ],
            check=True,
        )
        print("Installed the tested CatVTON requirements into the active environment.")
    print("Model checkpoints download lazily from Hugging Face on the first real inference.")


if __name__ == "__main__":
    main()
