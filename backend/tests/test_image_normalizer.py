from pathlib import Path

from PIL import Image, ImageDraw

from app.services.image_normalizer import ImageNormalizer


def test_normalizer_centers_alpha_and_preserves_square_canvas(tmp_path: Path) -> None:
    source = tmp_path / "segmented.png"
    output = tmp_path / "clean.png"
    image = Image.new("RGBA", (600, 800), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rectangle((170, 110, 430, 700), fill=(30, 30, 30, 255))
    image.save(source)
    report = ImageNormalizer(canvas_size=512).normalize(source, output)
    with Image.open(output) as result:
        assert result.size == (512, 512)
        assert result.mode == "RGBA"
        assert result.getchannel("A").getbbox() is not None
    assert report.foreground_ratio > 0.1
