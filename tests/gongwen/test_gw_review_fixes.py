"""最终审查发现的问题的回归测试。"""
import docx
import pytest
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls, qn

from gongwen.core.build import build_docx, default_filename
from gongwen.core.classify import classify
from gongwen.core.dates import normalize_date
from gongwen.core.model import Block, Document
from gongwen.core.reader import read_docx, read_text

W = nsdecls("w")


def _save(d, tmp_path, name="样例.docx"):
    p = tmp_path / name
    d.save(p)
    return p


# ---- I2: Word 自动编号 ----
NUMBERING = f"""<w:abstractNum {W} w:abstractNumId="90">
  <w:lvl w:ilvl="0"><w:start w:val="1"/><w:numFmt w:val="chineseCounting"/><w:lvlText w:val="%1、"/></w:lvl>
  <w:lvl w:ilvl="1"><w:start w:val="1"/><w:numFmt w:val="chineseCounting"/><w:lvlText w:val="（%2）"/></w:lvl>
  <w:lvl w:ilvl="2"><w:start w:val="1"/><w:numFmt w:val="decimal"/><w:lvlText w:val="%3."/></w:lvl>
</w:abstractNum>"""


def _numbered_doc():
    d = docx.Document()
    numbering = d.part.numbering_part.element
    numbering.insert(0, parse_xml(NUMBERING))
    numbering.append(parse_xml(f'<w:num {W} w:numId="90"><w:abstractNumId w:val="90"/></w:num>'))
    d.add_paragraph("标题")

    def item(text, lvl):
        p = d.add_paragraph(text)
        p._p.get_or_add_pPr().append(parse_xml(
            f'<w:numPr {W}><w:ilvl w:val="{lvl}"/><w:numId w:val="90"/></w:numPr>'))

    item("认真组织学习", 0)
    item("系统初评", 1)
    item("填写报告", 2)
    item("填写量表", 2)
    item("加强组织领导", 0)
    item("明确责任", 1)
    return d


def test_auto_numbering_rendered(tmp_path):
    texts = [b.text for b in read_docx(_save(_numbered_doc(), tmp_path))]
    assert texts == ["标题", "一、认真组织学习", "（一）系统初评", "1.填写报告", "2.填写量表",
                     "二、加强组织领导", "（一）明确责任"]


def test_auto_numbering_classified(tmp_path):
    ts = [b.t for b in classify(read_docx(_save(_numbered_doc(), tmp_path))).blocks]
    assert ts == ["title", "h1", "h2", "h3", "h3", "h1", "h2"]


# ---- I3 / Minor 2 / Minor 3: 修订插入、内容控件、分页符、嵌套表格 ----
def test_revision_insert_and_sdt(tmp_path):
    d = docx.Document()
    d.add_paragraph("标题")
    p = d.add_paragraph("已有")
    p._p.append(parse_xml(f'<w:ins {W} w:id="1" w:author="a"><w:r><w:t>修订插入</w:t></w:r></w:ins>'))
    p._p.append(parse_xml(f'<w:del {W} w:id="2" w:author="a"><w:r><w:delText>删除的</w:delText></w:r></w:del>'))
    p.add_run("文字。")
    d.element.body.insert(len(d.element.body) - 1, parse_xml(
        f'<w:sdt {W}><w:sdtContent><w:p><w:r><w:t>控件里的段落。</w:t></w:r></w:p></w:sdtContent></w:sdt>'))
    assert [b.text for b in read_docx(_save(d, tmp_path))] == ["标题", "已有修订插入文字。", "控件里的段落。"]


def test_page_break_splits(tmp_path):
    d = docx.Document()
    p = d.add_paragraph("前文")
    p._p.append(parse_xml(f'<w:r {W}><w:br w:type="page"/><w:t>后文。</w:t></w:r>'))
    assert [b.text for b in read_docx(_save(d, tmp_path))] == ["前文", "后文。"]


def test_nested_table_text(tmp_path):
    d = docx.Document()
    t = d.add_table(rows=1, cols=1)
    t.cell(0, 0).text = "外层"
    t.cell(0, 0).add_table(rows=1, cols=1).cell(0, 0).text = "内层"
    (block,) = read_docx(_save(d, tmp_path))
    assert block.rows == [["外层\n内层"]]


# ---- I4: 控制字符 ----
def test_control_chars_split_and_stripped(tmp_path):
    blocks = read_text("标题\x0b第二行\x0c正文\x07内容。\x00")
    assert [b.text for b in blocks] == ["标题", "第二行", "正文内容。"]
    build_docx(classify(blocks), tmp_path / "a.docx")  # 不报错


def test_from_dict_sanitizes(tmp_path):
    doc = Document.from_dict({"kind": "brief", "blocks": [{"t": "title", "text": "标\x01题"}]})
    assert doc.blocks[0].text == "标题"
    build_docx(doc, tmp_path / "b.docx")


# ---- I5 / I6: 附件写法 ----
def types_texts(text):
    return [(b.t, b.text) for b in classify(read_text(text)).blocks]


def test_inline_numbered_attachment():
    assert types_texts("标题\n正文。\n附件：1.《量表》\n2.《说明》")[-2:] == [
        ("attachment", "《量表》"), ("attachment", "《说明》")]


def test_single_unnumbered_attachment():
    assert types_texts("标题\n正文。\n附件：\n《量表》")[-1] == ("attachment", "《量表》")
    # 第一个无序号段落算作唯一附件后，附件区结束
    assert types_texts("标题\n正文。\n附件\n《量表》\n特此通知。")[-1] == ("body", "特此通知。")


# ---- I7: ○ 写的日期 ----
def test_circle_zero_dates():
    assert normalize_date("二○二六年八月二十四日") == "2026年8月24日"
    assert normalize_date("二Ｏ二六年八月二十四日") == "2026年8月24日"
    assert [t for t, _ in types_texts("标题\n正文。\n评估矫治中心\n二○二六年八月二十四日")] == [
        "title", "body", "signer", "date"]


# ---- Minor 4: 文件名 ----
def test_filename_control_chars_length_and_dots():
    assert default_filename(Document("brief", [Block("title", "关于\t通知. ")])) == "关于通知.docx"
    long = "很长" * 100
    name = default_filename(Document("brief", [Block("title", long)]))
    assert name.endswith(".docx") and len(name) <= 85
