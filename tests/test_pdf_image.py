import pymupdf
import pytest

from app.core.converters.pdf_image import image_to_pdf, images_to_single_pdf, pdf_to_image
from app.core.errors import ConversionError
from app.core.options import Options


def test_pdf_to_image_pages(sample_pdf, tmp_path):
    out = pdf_to_image(sample_pdf, tmp_path / "o", Options(dpi=150))
    assert len(out) == 3 and all(p.suffix == ".png" for p in out)
    assert pymupdf.Pixmap(out[0]).width == pytest.approx(595 * 150 / 72, rel=0.02)


def test_image_to_pdf(sample_png, tmp_path):
    (pdf,) = image_to_pdf(sample_png, tmp_path / "o", Options())
    assert pymupdf.open(pdf).page_count == 1


def test_images_to_single_pdf(sample_png, tmp_path):
    out = images_to_single_pdf([sample_png, sample_png], tmp_path / "m.pdf")
    assert pymupdf.open(out).page_count == 2


def test_encrypted_pdf(encrypted_pdf, tmp_path):
    with pytest.raises(ConversionError, match="PDF 已加密"):
        pdf_to_image(encrypted_pdf, tmp_path, Options())


def test_corrupt_pdf(corrupt_pdf, tmp_path):
    with pytest.raises(ConversionError, match="已损坏"):
        pdf_to_image(corrupt_pdf, tmp_path, Options())


def test_corrupt_image(tmp_path):
    bad = tmp_path / "坏.png"
    bad.write_bytes(b"xx")
    with pytest.raises(ConversionError, match="已损坏"):
        image_to_pdf(bad, tmp_path / "o", Options())
