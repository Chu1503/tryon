from __future__ import annotations

import io
import os
import sys
import time
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))


def image_bytes(kind: str) -> bytes:
    if kind == "person":
        image = Image.new("RGB", (768, 1024), "#d8d4ca")
        draw = ImageDraw.Draw(image)
        draw.ellipse((294, 80, 474, 260), fill="#8b6955")
        draw.rounded_rectangle((250, 240, 518, 760), radius=110, fill="#aaa79e")
        draw.rectangle((280, 730, 365, 990), fill="#4c4a48")
        draw.rectangle((403, 730, 488, 990), fill="#4c4a48")
    else:
        image = Image.new("RGB", (700, 700), "white")
        draw = ImageDraw.Draw(image)
        draw.polygon([(205,150),(95,250),(155,365),(225,325),(225,590),(475,590),(475,325),(545,365),(605,250),(495,150),(425,205),(275,205)], fill="#25272b")
        draw.ellipse((285, 155, 415, 245), fill="white")
    buffer = io.BytesIO()
    image.save(buffer, "JPEG", quality=96)
    return buffer.getvalue()


def main() -> None:
    smoke_data = ROOT / ".testdata-smoke"
    # Explicit assignment is intentional: inherited shell variables and the
    # project's .env must never let a smoke test touch the real wardrobe.
    os.environ["DATA_DIR"] = str(smoke_data)
    os.environ["DATABASE_URL"] = f"sqlite:///{(smoke_data / 'wardrobe.db').as_posix()}"
    os.environ["REMBG_MODEL"] = "u2netp"
    os.environ["MOCK_VTON"] = "true"
    from fastapi.testclient import TestClient
    from app.main import app

    with TestClient(app) as client:
        person = image_bytes("person")
        response = client.post("/api/user/body-images", files={"front":("front.jpg",person,"image/jpeg"),"back":("back.jpg",person,"image/jpeg")})
        response.raise_for_status()
        garment_image = image_bytes("garment")
        response = client.post(
            "/api/garments",
            data={"name":"Smoke Test Tee","category":"T-Shirt","brand":"Local","color":"Black"},
            files={"front":("front.jpg",garment_image,"image/jpeg"),"back":("back.jpg",garment_image,"image/jpeg")},
        )
        if not response.is_success:
            print(response.text)
        response.raise_for_status()
        garment = response.json()
        assert garment["clean_front_url"] and garment["clean_back_url"]
        front_only_response = client.post(
            "/api/garments",
            data={"name": "Front Only Tee", "category": "T-Shirt"},
            files={"front": ("front.jpg", garment_image, "image/jpeg")},
        )
        front_only_response.raise_for_status()
        front_only = front_only_response.json()
        assert front_only["clean_front_url"]
        assert front_only["raw_back_url"] is None
        assert front_only["clean_back_url"] is None
        assert front_only["back_status"] == "not_generated"
        response = client.post(f"/api/garments/{garment['id']}/generate")
        response.raise_for_status()
        deadline = time.time() + 10
        while time.time() < deadline:
            garment = client.get(f"/api/garments/{garment['id']}").json()
            if garment["front_status"] == garment["back_status"] == "ready":
                break
            time.sleep(0.1)
        assert garment["front_status"] == garment["back_status"] == "ready", garment
        assert client.get(f"/api/garments/{garment['id']}/tryon/front").status_code == 200
        assert client.get(f"/api/garments/{garment['id']}/tryon/back").status_code == 200
        cached = client.post(f"/api/garments/{garment['id']}/generate").json()["cached_views"]
        assert sorted(cached) == ["back", "front"]
        response = client.patch(
            f"/api/garments/{garment['id']}/images",
            files={"front": ("replacement.jpg", garment_image, "image/jpeg")},
        )
        response.raise_for_status()
        replaced = response.json()
        assert replaced["front_status"] == "not_generated"
        assert replaced["back_status"] == "ready"
        back_cache = client.post(f"/api/garments/{garment['id']}/generate/back").json()["cached_views"]
        assert back_cache == ["back"]
        response = client.post(
            "/api/user/body-images",
            files={"front": ("new-front.jpg", person, "image/jpeg")},
        )
        response.raise_for_status()
        invalidated = client.get(f"/api/garments/{garment['id']}").json()
        assert invalidated["front_status"] == invalidated["back_status"] == "not_generated"
        client.delete(f"/api/garments/{front_only['id']}").raise_for_status()
        print(f"PASS: optional back + rembg -> normalize -> mock VTON -> front/back cache ({garment['id']})")


if __name__ == "__main__":
    main()
