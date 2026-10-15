import openpyxl
import pytest

from app.core.converters.pdf_excel import pdf_to_excel
from app.core.errors import ConversionError
from app.core.options import Options


def test_pdf_to_excel(sample_table_pdf, tmp_path):
    (out,) = pdf_to_excel(sample_table_pdf, tmp_path / "o", Options())
    ws = openpyxl.load_workbook(out)["第1页"]
    rows = [[c.value for c in r] for r in ws.iter_rows(max_row=3)]
    assert rows == [["姓名", "分数"], ["张三", "90"], ["李四", "85"]]


def test_pdf_to_excel_no_tables(sample_pdf, tmp_path):
    with pytest.raises(ConversionError, match="未找到表格"):
        pdf_to_excel(sample_pdf, tmp_path, Options())


def test_pdf_to_excel_corrupt(corrupt_pdf, tmp_path):
    with pytest.raises(ConversionError, match="已损坏"):
        pdf_to_excel(corrupt_pdf, tmp_path, Options())


def test_clean_cell_strips_control_chars():
    from app.core.converters.pdf_excel import clean_cell
    assert clean_cell("a\x07b") == "ab"
    assert clean_cell(None) is None
