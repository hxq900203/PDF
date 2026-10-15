import pymupdf
import pytest

from app.core.converters import office
from app.core.converters.office import find_soffice, office_to_pdf
from app.core.errors import ConversionError
from app.core.options import Options
from conftest import needs_soffice


@needs_soffice
def test_docx_to_pdf(sample_docx, tmp_path):
    (pdf,) = office_to_pdf(sample_docx, tmp_path / "o", Options())
    assert "你好世界" in pymupdf.open(pdf).load_page(0).get_text()


@needs_soffice
def test_xlsx_to_pdf(sample_xlsx, tmp_path):
    (pdf,) = office_to_pdf(sample_xlsx, tmp_path / "o", Options())
    assert "名称" in pymupdf.open(pdf).load_page(0).get_text()


@needs_soffice
def test_corrupt_docx(tmp_path):
    bad = tmp_path / "坏.docx"
    bad.write_bytes(b"\x00\x01garbage")
    with pytest.raises(ConversionError):
        office_to_pdf(bad, tmp_path / "o", Options())


def test_missing_soffice(monkeypatch, sample_docx, tmp_path):
    monkeypatch.setattr(office, "find_soffice", lambda: None)
    with pytest.raises(ConversionError, match="未找到 LibreOffice"):
        office_to_pdf(sample_docx, tmp_path, Options())


def test_env_override(monkeypatch, tmp_path):
    fake = tmp_path / "soffice"
    fake.touch()
    monkeypatch.setenv("FC_SOFFICE", str(fake))
    assert find_soffice() == fake


def test_bundled_preferred(monkeypatch, tmp_path):
    monkeypatch.delenv("FC_SOFFICE", raising=False)
    exe = tmp_path / "libreoffice" / "program" / "soffice.exe"
    exe.parent.mkdir(parents=True)
    exe.touch()
    monkeypatch.setattr(office, "app_dir", lambda: tmp_path)
    assert find_soffice() == exe
