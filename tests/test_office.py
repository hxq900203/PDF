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


@pytest.mark.parametrize("name,data", [
    ("空.docx", b""), ("文本.docx", "这是文本".encode()), ("文本.xlsx", b"plain text"),
    ("文本.doc", b"plain text"), ("空.xls", b""),
])
def test_disguised_office_rejected(tmp_path, name, data):
    f = tmp_path / name
    f.write_bytes(data)
    with pytest.raises(ConversionError, match="已损坏"):
        office_to_pdf(f, tmp_path / "o", Options())


def test_legacy_doc_magic_accepted(monkeypatch, tmp_path):
    f = tmp_path / "旧.doc"
    f.write_bytes(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\x00" * 100)
    monkeypatch.setattr(office, "find_soffice", lambda: None)
    with pytest.raises(ConversionError, match="未找到 LibreOffice"):  # 通过了预检，才走到查找 soffice
        office_to_pdf(f, tmp_path / "o", Options())
