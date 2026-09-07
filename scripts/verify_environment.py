from __future__ import annotations

import importlib
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODULES = ("fastapi", "sqlalchemy", "PIL", "cv2", "numpy", "rembg", "torch", "diffusers", "transformers")


def main() -> None:
    failures: list[str] = []
    print(f"Python: {sys.version.split()[0]} ({sys.executable})")
    for name in MODULES:
        try:
            module = importlib.import_module(name)
            version = getattr(module, "__version__", "installed")
            print(f"[ok] {name}: {version}")
        except Exception as exc:
            failures.append(name)
            print(f"[missing] {name}: {exc}")

    catvton = PROJECT_ROOT / "models" / "CatVTON" / "model" / "pipeline.py"
    print(f"[{'ok' if catvton.is_file() else 'missing'}] CatVTON source: {catvton}")
    if catvton.is_file():
        sys.path.append(str(catvton.parents[1]))
        try:
            from PIL import Image

            if not hasattr(Image, "LINEAR"):
                Image.LINEAR = Image.Resampling.BILINEAR  # type: ignore[attr-defined]
            importlib.import_module("model.pipeline")
            importlib.import_module("model.cloth_masker")
            print("[ok] CatVTON pipeline and body masker imports")
        except Exception as exc:
            failures.append("CatVTON imports")
            print(f"[missing] CatVTON imports: {exc}")
    else:
        failures.append("CatVTON source")
    try:
        import torch

        if torch.cuda.is_available():
            properties = torch.cuda.get_device_properties(0)
            print(f"[ok] CUDA: {torch.cuda.get_device_name(0)} ({properties.total_memory / 1024**3:.1f} GiB)")
        else:
            failures.append("CUDA")
            print("[missing] CUDA is not available to PyTorch")
    except Exception:
        pass

    if failures:
        raise SystemExit(f"Environment verification failed: {', '.join(failures)}")
    print("Environment verification passed.")


if __name__ == "__main__":
    main()
