import docx
import pytest
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls
from test_gw_review_fixes import _numbered_doc

from gongwen.core.reader import read_docx

W = nsdecls("w")


def plain(d):
    d.add_paragraph("标题")
    t = d.add_table(rows=2, cols=2)
    for i, row in enumerate([["监区", "人数"], ["一监区", "12"]]):
        for j, v in enumerate(row):
            t.cell(i, j).text = v
    d.add_paragraph("　　正文。\t")


def soft_break(d):
    p = d.add_paragraph()
    r = p.add_run("关于组织学习临释罪犯再犯风险评估")
    r.add_break()
    p.add_run("相关内容的通知")


def revisions(d):
    d.add_paragraph("标题")
    p = d.add_paragraph("已有")
    p._p.append(parse_xml(f'<w:ins {W} w:id="1" w:author="a"><w:r><w:t>修订插入</w:t></w:r></w:ins>'))
    p._p.append(parse_xml(f'<w:del {W} w:id="2" w:author="a"><w:r><w:delText>删除的</w:delText></w:r></w:del>'))
    p.add_run("文字。")
    d.element.body.insert(len(d.element.body) - 1, parse_xml(
        f'<w:sdt {W}><w:sdtContent><w:p><w:r><w:t>控件里的段落。</w:t></w:r></w:p></w:sdtContent></w:sdt>'))


def page_break(d):
    p = d.add_paragraph("前文")
    p._p.append(parse_xml(f'<w:r {W}><w:br w:type="page"/><w:t>后文。</w:t></w:r>'))


def nested(d):
    t = d.add_table(rows=1, cols=1)
    t.cell(0, 0).text = "外层"
    t.cell(0, 0).add_table(rows=1, cols=1).cell(0, 0).text = "内层"


def merged(d):
    t = d.add_table(rows=3, cols=3)
    for i in range(3):
        for j in range(3):
            t.cell(i, j).text = f"{i}{j}"
    t.cell(0, 0).merge(t.cell(0, 1))   # 横向合并
    t.cell(1, 2).merge(t.cell(2, 2))   # 纵向合并


def tab_and_empty_table(d):
    d.add_paragraph("甲\t乙")
    d.add_table(rows=1, cols=2)        # 全空表格应丢弃
    d.add_paragraph("丙")


BUILDERS = [plain, soft_break, revisions, page_break, nested, merged, tab_and_empty_table]


@pytest.mark.parametrize("builder", BUILDERS, ids=lambda f: f.__name__)
def test_same_as_python(js, tmp_path, builder):
    d = docx.Document()
    builder(d)
    p = tmp_path / "中文 样例.docx"
    d.save(p)
    assert js("read", p) == [b.to_dict() for b in read_docx(p)]


def test_auto_numbering(js, tmp_path):
    p = tmp_path / "编号.docx"
    _numbered_doc().save(p)
    assert js("read", p) == [b.to_dict() for b in read_docx(p)]


@pytest.mark.parametrize("name,data,msg", [
    ("旧.doc", b"\xd0\xcf\x11\xe0", "暂不支持老版 .doc 文件，请先用「文件转换器」转为 .docx，或复制文字后点「粘贴文字」"),
    ("坏.docx", b"not a zip", "文件已损坏或无法读取"),
])
def test_errors(js, tmp_path, name, data, msg):
    f = tmp_path / name
    f.write_bytes(data)
    with pytest.raises(RuntimeError) as e:
        js("read", f)
    assert e.value.args == (msg, 2)


def test_empty(js, tmp_path):
    p = tmp_path / "空.docx"
    docx.Document().save(p)
    with pytest.raises(RuntimeError) as e:
        js("read", p)
    assert e.value.args == ("没有读到任何文字", 2)
