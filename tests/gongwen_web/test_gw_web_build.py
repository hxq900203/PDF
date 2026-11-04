"""同一份文档分别用 Python build_docx 与 JS buildDocx 生成，读回后逐项比对。"""
import json
import shutil
import subprocess
import zipfile

import docx
import pytest
from docx.oxml.ns import qn
from samples import BRIEF, NOTICE

from gongwen.core.build import build_docx
from gongwen.core.classify import classify
from gongwen.core.model import Block, Document
from gongwen.core.reader import read_text

SLOTS = ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs")


def notice_with_table():
    d = classify(read_text(NOTICE))
    d.blocks.insert(4, Block("table", rows=[["监区", "人数"], ["一监区", "12"]]))
    return d


DOCS = {
    "notice": lambda: classify(read_text(NOTICE)),
    "brief": lambda: classify(read_text(BRIEF)),
    "table": notice_with_table,
    "tabs": lambda: Document("brief", [Block("title", "标题"), Block("body", "甲\t乙"), Block("h2", "（一）"),
                                       Block("table", rows=[["", "x"]])]),
}


def run_props(r):
    rf = r._element.rPr.rFonts
    return (r.text, tuple(rf.get(qn(a)) for a in SLOTS), r.font.size, r.font.bold)


def para_props(p):
    pf = p.paragraph_format
    ind = p._p.pPr.find(qn("w:ind")) if p._p.pPr is not None else None
    return (p.text, p.alignment, pf.first_line_indent, None if ind is None else ind.get(qn("w:firstLineChars")),
            pf.line_spacing, pf.line_spacing_rule, pf.space_before, pf.space_after,
            [run_props(r) for r in p.runs])


def summary(path):
    d = docx.Document(str(path))
    s = d.sections[0]
    grid = s._sectPr.find(qn("w:docGrid"))
    footer = s.footer.paragraphs[0]
    return {
        "paragraphs": [para_props(p) for p in d.paragraphs],
        "section": (s.page_width, s.page_height, s.top_margin, s.bottom_margin, s.left_margin, s.right_margin,
                    s.header_distance, s.footer_distance, grid.get(qn("w:type")), grid.get(qn("w:linePitch"))),
        "footer": (footer.alignment, "PAGE" in footer._p.xml, footer.runs[0].font.size),
        "tables": [(t.style.name, t.alignment,
                    [[para_props(c.paragraphs[0]) for c in row.cells] for row in t.rows]) for t in d.tables],
    }


def js_build(js, tmp_path, doc, subs=None):
    src = tmp_path / "doc.json"
    src.write_text(json.dumps(doc.to_dict(), ensure_ascii=False), encoding="utf-8")
    out = tmp_path / "js.docx"
    args = ["build", src, out]
    if subs is not None:
        sf = tmp_path / "subs.json"
        sf.write_text(json.dumps(subs, ensure_ascii=False), encoding="utf-8")
        args.append(sf)
    js(*args)
    return out


@pytest.mark.parametrize("name", DOCS)
def test_same_as_python(js, tmp_path, name):
    doc = DOCS[name]()
    py = build_docx(doc, tmp_path / "py.docx")
    assert summary(js_build(js, tmp_path, doc)) == summary(py)


def test_settings_and_defaults(js, tmp_path):
    out = js_build(js, tmp_path, DOCS["notice"]())
    z = zipfile.ZipFile(out)
    settings = z.read("word/settings.xml").decode()
    for tag in ("spaceForUL", "balanceSingleByteDoubleByteWidth", "doNotLeaveBackslashAlone", "ulTrailSpace",
                "doNotExpandShiftReturn", "adjustLineHeightInTable"):
        assert f"<w:{tag}/>" in settings
    assert 'w:name="compatibilityMode"' in settings and 'w:val="15"' in settings
    assert '<w:characterSpacingControl w:val="compressPunctuation"/>' in settings
    styles = z.read("word/styles.xml").decode()
    assert 'w:eastAsia="zh-CN"' in styles and '<w:kern w:val="2"/>' in styles


def test_font_table_alt_names(js, tmp_path):
    out = js_build(js, tmp_path, DOCS["notice"]())
    ft = docx.oxml.parse_xml(zipfile.ZipFile(out).read("word/fontTable.xml"))
    fonts = {f.get(qn("w:name")): f for f in ft.findall(qn("w:font"))}
    alt = lambda n: fonts[n].find(qn("w:altName")).get(qn("w:val"))
    fam = lambda n: fonts[n].find(qn("w:family")).get(qn("w:val"))
    assert alt("方正小标宋简体") == "方正小标宋_GBK" and alt("仿宋_GB2312") == "仿宋"
    assert alt("楷体_GB2312") == "楷体" and alt("黑体") == "方正黑体_GBK"
    assert fam("黑体") == "swiss" and fam("仿宋_GB2312") == "roman"
    assert fonts["黑体"].find(qn("w:charset")).get(qn("w:val")) == "86"


@pytest.mark.skipif(shutil.which("soffice") is None, reason="无 LibreOffice")
def test_libreoffice_opens(js, tmp_path):
    out = js_build(js, tmp_path, DOCS["table"]())
    subprocess.run(["soffice", "--headless", "--convert-to", "pdf", "--outdir", str(tmp_path), str(out)],
                   capture_output=True, timeout=120)
    import pymupdf
    pdf = tmp_path / "js.pdf"
    assert pdf.is_file() and "相关内容的通知" in pymupdf.open(pdf)[0].get_text()
