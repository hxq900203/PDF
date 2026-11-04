import docx
import pytest

from gongwen.core.errors import GongwenError
from gongwen.core.reader import read_docx, read_text


def _save(d, tmp_path, name="中文 样例.docx"):
    p = tmp_path / name
    d.save(p)
    return p


def test_read_docx_order_and_table(tmp_path):
    d = docx.Document()
    d.add_paragraph("标题")
    t = d.add_table(rows=2, cols=2)
    for i, row in enumerate([["监区", "人数"], ["一监区", "12"]]):
        for j, v in enumerate(row):
            t.cell(i, j).text = v
    d.add_paragraph("正文。")
    blocks = read_docx(_save(d, tmp_path))
    assert [b.t for b in blocks] == ["body", "table", "body"]
    assert blocks[1].rows == [["监区", "人数"], ["一监区", "12"]]


def test_soft_line_break_splits(tmp_path):
    d = docx.Document()
    p = d.add_paragraph()
    r = p.add_run("关于组织学习临释罪犯再犯风险评估")
    r.add_break()
    p.add_run("相关内容的通知")
    blocks = read_docx(_save(d, tmp_path))
    assert [b.text for b in blocks] == ["关于组织学习临释罪犯再犯风险评估", "相关内容的通知"]


def test_clean_and_drop_empty():
    assert [b.text for b in read_text("　　一、标题\r\n\r\n  正文。\t\n\r末行")] == ["一、标题", "正文。", "末行"]
    assert all(b.t == "body" for b in read_text("a\nb"))


def test_doc_rejected(tmp_path):
    f = tmp_path / "旧.doc"
    f.write_bytes(b"\xd0\xcf\x11\xe0")
    with pytest.raises(GongwenError, match="老版 .doc"):
        read_docx(f)


def test_corrupt(tmp_path):
    f = tmp_path / "坏.docx"
    f.write_bytes(b"not a zip")
    with pytest.raises(GongwenError, match="已损坏"):
        read_docx(f)


def test_empty(tmp_path):
    with pytest.raises(GongwenError, match="没有读到任何文字"):
        read_docx(_save(docx.Document(), tmp_path))
    with pytest.raises(GongwenError, match="没有读到任何文字"):
        read_text("  \n ")
