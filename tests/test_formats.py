from pathlib import Path

from app.core.formats import LABELS, OUTPUT_EXT, detect_format


def test_detect_format_case_insensitive():
    assert detect_format(Path("a/报告.DOCX")) == "word"
    assert detect_format(Path("x.Xls")) == "excel"
    assert detect_format(Path("p.JPG")) == "image"
    assert detect_format(Path("d.pdf")) == "pdf"
    assert detect_format(Path("n.txt")) is None


def test_output_ext_and_labels():
    assert OUTPUT_EXT == {"word": ".docx", "excel": ".xlsx", "pdf": ".pdf", "image": ".png"}
    assert LABELS == {"pdf": "PDF", "word": "Word", "excel": "Excel", "image": "PNG 图片"}
