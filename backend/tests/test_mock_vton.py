from pathlib import Path

from PIL import Image, ImageDraw

from app.services.catvton_service import MockVirtualTryOnService


def test_mock_vton_writes_png(tmp_path: Path) -> None:
    person = tmp_path / "person.jpg"
    garment = tmp_path / "garment.png"
    output = tmp_path / "tryon.png"
    Image.new("RGB", (512, 768), "#d9d5ca").save(person)
    cloth = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
    ImageDraw.Draw(cloth).rectangle((100, 80, 412, 410), fill=(25, 25, 28, 255))
    cloth.save(garment)
    MockVirtualTryOnService().generate(str(person), str(garment), "T-Shirt", str(output))
    with Image.open(output) as result:
        assert result.format == "PNG"
        assert result.size == (512, 768)
