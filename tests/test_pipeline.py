import pymupdf
import pytest

from app.core.errors import ConversionError
from app.core.options import Options
from app.core.pipeline import convert_file, merge_images_to_pdf
from conftest import needs_soffice


def test_pdf_to_images_named(sample_pdf, tmp_path):
    out = convert_file(sample_pdf, "image", tmp_path / "o", Options())
    assert [p.name for p in out] == ["中文 样例_第1页.png", "中文 样例_第2页.png", "中文 样例_第3页.png"]
    assert all(p.is_file() for p in out)


def test_default_out_dir_is_source_dir(sample_png):
    (pdf,) = convert_file(sample_png, "pdf", None, Options())
    assert pdf.parent == sample_png.parent and pdf.name == "中文 样例.pdf"


def test_same_stem_no_overwrite(tmp_path, make_png):
    a = make_png(tmp_path / "a" / "报告.png")
    b = make_png(tmp_path / "b" / "报告.png")
    out = tmp_path / "out"
    assert convert_file(a, "pdf", out, Options())[0].name == "报告.pdf"
    assert convert_file(b, "pdf", out, Options())[0].name == "报告 (1).pdf"


def test_disabled_target(sample_png, tmp_path):
    with pytest.raises(ConversionError, match="不支持转换为该格式"):
        convert_file(sample_png, "word", tmp_path, Options())


def test_unknown_format(tmp_path):
    f = tmp_path / "a.txt"
    f.write_text("x")
    with pytest.raises(ConversionError, match="不支持的文件格式"):
        convert_file(f, "pdf", tmp_path, Options())


def test_corrupt_raises_cleanly(corrupt_pdf, tmp_path):
    with pytest.raises(ConversionError):
        convert_file(corrupt_pdf, "image", tmp_path / "o", Options())
    assert not (tmp_path / "o").exists() or not any((tmp_path / "o").iterdir())


def test_merge_images(sample_png, tmp_path):
    p = merge_images_to_pdf([sample_png, sample_png], tmp_path / "o")
    assert p.name == "中文 样例_合并.pdf" and pymupdf.open(p).page_count == 2


@needs_soffice
def test_two_hop_docx_to_png(sample_docx, tmp_path):
    out = convert_file(sample_docx, "image", tmp_path / "o", Options())
    assert [p.name for p in out] == ["中文 样例.png"]
