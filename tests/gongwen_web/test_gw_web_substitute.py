import zipfile

import docx
from docx.oxml.ns import qn
from samples import NOTICE
from test_gw_web_build import js_build, summary

from gongwen.core.classify import classify
from gongwen.core.reader import read_text


def fonts(p):
    return p.runs[0]._element.rPr.rFonts.get(qn("w:eastAsia"))


def test_substitutes_applied(js, tmp_path):
    doc = classify(read_text(NOTICE))
    out = js_build(js, tmp_path, doc, {"方正小标宋简体": "宋体", "仿宋_GB2312": "仿宋"})
    ps = docx.Document(str(out)).paragraphs
    assert fonts(ps[0]) == "宋体" and ps[0].runs[0].font.bold is True
    rf = ps[3].runs[0]._element.rPr.rFonts
    assert {rf.get(qn(a)) for a in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs")} == {"仿宋"}
    assert fonts(ps[4]) == "黑体" and fonts(ps[5]) == "楷体_GB2312"
    # 其他参数与默认导出相同
    (tmp_path / "d").mkdir()
    default = summary(js_build(js, tmp_path / "d", doc))
    sub = summary(out)
    assert sub["section"] == default["section"] and sub["footer"] == default["footer"]
    strip = lambda s: [(p[:8]) for p in s["paragraphs"]]
    assert strip(sub) == strip(default)


def test_non_compensating_substitute_not_bold(js, tmp_path):
    out = js_build(js, tmp_path, classify(read_text(NOTICE)), {"方正小标宋简体": "华文中宋"})
    p = docx.Document(str(out)).paragraphs[0]
    assert fonts(p) == "华文中宋" and p.runs[0].font.bold is False


def test_empty_substitutes_identical(js, tmp_path):
    doc = classify(read_text(NOTICE))
    a = js_build(js, tmp_path, doc, {})
    (tmp_path / "b").mkdir()
    b = js_build(js, tmp_path / "b", doc)
    read = lambda p: zipfile.ZipFile(p).read("word/document.xml")
    assert read(a) == read(b)
