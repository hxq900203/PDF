import docx
import pytest

from app.core.converters.pdf_word import pdf_to_word
from app.core.errors import ConversionError
from app.core.options import Options


def test_pdf_to_word(sample_pdf, tmp_path):
    (out,) = pdf_to_word(sample_pdf, tmp_path / "o", Options())
    text = "\n".join(p.text for p in docx.Document(out).paragraphs)
    assert "第1页" in text and "第3页" in text


def test_pdf_to_word_encrypted(encrypted_pdf, tmp_path):
    with pytest.raises(ConversionError, match="PDF 已加密"):
        pdf_to_word(encrypted_pdf, tmp_path, Options())
