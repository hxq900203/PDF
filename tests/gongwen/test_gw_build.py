import docx
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Cm, Pt
from samples import BRIEF, NOTICE

from gongwen.core.build import build_docx, default_filename
from gongwen.core.classify import classify
from gongwen.core.model import Block, Document
from gongwen.core.reader import read_text

SLOTS = ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs")


def font(p):
    r = p.runs[0]
    return r._element.rPr.rFonts.get(qn("w:eastAsia")), r.font.size.pt


def first_line_chars(p):
    ind = p._p.pPr.find(qn("w:ind"))
    return None if ind is None else ind.get(qn("w:firstLineChars"))


def build(tmp_path, text, name="通知.docx"):
    out = build_docx(classify(read_text(text)), tmp_path / name)
    return docx.Document(str(out))


def test_fonts_and_sizes(tmp_path):
    ps = build(tmp_path, NOTICE).paragraphs
    assert font(ps[0]) == ("方正小标宋简体", 22) and ps[0].alignment == WD_ALIGN_PARAGRAPH.CENTER
    assert first_line_chars(ps[0]) is None
    assert ps[1].text == "相关内容的通知"
    assert font(ps[2]) == ("黑体", 16) and first_line_chars(ps[2]) is None
    body, h1, h2, h3 = ps[3], ps[4], ps[5], ps[6]
    assert font(h1) == ("黑体", 16) and font(h2) == ("楷体_GB2312", 16)
    assert font(h3) == ("仿宋_GB2312", 16) and font(body) == ("仿宋_GB2312", 16)
    assert all(first_line_chars(p) == "200" for p in (body, h1, h2, h3))
    assert body.alignment == WD_ALIGN_PARAGRAPH.JUSTIFY
    for p in ps:
        assert p.paragraph_format.line_spacing == Pt(26)
        assert p.paragraph_format.space_after == Pt(8) and p.paragraph_format.space_before == Pt(0)
    assert not any(r.bold for p in ps for r in p.runs)


def test_four_font_slots(tmp_path):
    for p in build(tmp_path, NOTICE).paragraphs:
        for r in p.runs:
            rf = r._element.rPr.rFonts
            assert len({rf.get(qn(a)) for a in SLOTS}) == 1


def test_page_setup(tmp_path):
    d = build(tmp_path, NOTICE)
    s = d.sections[0]
    def near(a, cm):  # Word 以 twip 存储，换算有舍入
        return abs(a - Cm(cm)) < Cm(0.01)
    assert near(s.page_width, 21) and near(s.page_height, 29.7)
    assert all(near(m, 2.54) for m in (s.top_margin, s.bottom_margin))
    assert all(near(m, 3.17) for m in (s.left_margin, s.right_margin))
    assert near(s.header_distance, 1.5) and near(s.footer_distance, 1.75)
    grid = s._sectPr.find(qn("w:docGrid"))
    assert grid.get(qn("w:type")) == "lines" and grid.get(qn("w:linePitch")) == "312"
    footer = s.footer.paragraphs[0]
    assert footer.alignment == WD_ALIGN_PARAGRAPH.CENTER and "PAGE" in footer._p.xml


def test_attachments_and_signoff(tmp_path):
    ps = build(tmp_path, NOTICE).paragraphs
    assert [p.text for p in ps][-6:] == ["附件", "1、《罪犯再犯风险评估量表（成年男犯）》及填写说明",
                                         "2、《评估报告模板》", "", "评估矫治中心", "2026年8月24日"]
    assert ps[-6].alignment == WD_ALIGN_PARAGRAPH.JUSTIFY and first_line_chars(ps[-5]) == "200"
    assert all(p.alignment == WD_ALIGN_PARAGRAPH.RIGHT for p in ps[-3:])
    assert font(ps[-1]) == ("仿宋_GB2312", 16)


def test_brief_blank_after_title(tmp_path):
    ps = build(tmp_path, BRIEF, "简报.docx").paragraphs
    assert ps[0].text == "心理为钥，精准疏导解心结" and ps[1].text == ""
    assert ps[2].text == "近日，某监区开展心理疏导活动。"


def test_table(tmp_path):
    doc = Document("brief", [Block("title", "标题"), Block("table", rows=[["监区", "人数"], ["一监区", "12"]]),
                             Block("body", "正文。")])
    d = docx.Document(str(build_docx(doc, tmp_path / "表.docx")))
    t = d.tables[0]
    assert t.style.name == "Table Grid"
    head, cell = t.cell(0, 0).paragraphs[0], t.cell(1, 0).paragraphs[0]
    assert font(head) == ("黑体", 14) and font(cell) == ("仿宋_GB2312", 14)
    assert cell.alignment == WD_ALIGN_PARAGRAPH.CENTER
    texts = [p.text for p in d.paragraphs]
    assert texts == ["标题", "", "", "正文。"]  # 标题、简报空行、表后空行、正文


def test_default_filename():
    assert default_filename(Document("notice", [Block("title", "关于“A/B”的"), Block("title", "通知")])) == "关于“AB”的通知.docx"
    assert default_filename(Document("brief", [Block("body", "x")])) == "公文.docx"
    assert default_filename(Document("brief", [Block("title", '<>:"|?*')])) == "公文.docx"
