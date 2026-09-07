from pathlib import Path

from PIL import Image, ImageDraw

from app.config import Settings
from app.services.body_processor import BodyProcessor
from app.services.storage import LocalStorage


def test_trim_transparent_removes_empty_canvas(tmp_path: Path) -> None:
    settings = Settings(data_dir=tmp_path)
    storage = LocalStorage(settings)
    storage.initialize()
    source = storage.root / "user" / "cutout.png"
    image = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
    ImageDraw.Draw(image).rectangle((30, 20, 69, 79), fill=(20, 30, 40, 255))
    image.save(source)

    relative = BodyProcessor(settings, storage).trim_transparent("user/cutout.png")

    with Image.open(storage.resolve(relative)) as trimmed:
        assert trimmed.size == (46, 66)
        assert trimmed.getchannel("A").getbbox() == (3, 3, 43, 63)
