"""按单位公文格式生成 .docx。排版参数取自用户 unit-doc-format skill 的 gw_build.py。"""
import re
from pathlib import Path

from docx import Document as new_docx
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

from .dates import normalize_date
from .model import Document

FS = "仿宋_GB2312"      # 正文
HT = "黑体"             # 一级标题、主送机关
KT = "楷体_GB2312"      # 二级标题
XBS = "方正小标宋简体"   # 文章标题
SAN = Pt(16)   # 三号
ER = Pt(22)    # 二号
SI = Pt(14)    # 四号（表格）
LINE = Pt(26)  # 固定值 26 磅
AFTER = Pt(8)  # 段后 8 磅

FONTS = {"addressee": HT, "h1": HT, "h2": KT, "h3": FS, "body": FS}
_ALIGN = {"both": WD_ALIGN_PARAGRAPH.JUSTIFY, "center": WD_ALIGN_PARAGRAPH.CENTER,
          "right": WD_ALIGN_PARAGRAPH.RIGHT}


def _set_font(run, name, size):
    run.font.size = size
    run.font.bold = False
    rpr = run._element.get_or_add_rPr()
    rf = rpr.find(qn("w:rFonts"))
    if rf is None:
        rf = OxmlElement("w:rFonts")
        rpr.insert(0, rf)
    # 四个字体槽都设同一字体，数字和英文也用所在段落的中文字体
    for a in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        rf.set(qn(a), name)
    rf.set(qn("w:hint"), "eastAsia")


def _para(doc, text, font, size, align="both", indent=True):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.alignment = _ALIGN[align]
    pf.line_spacing_rule = WD_LINE_SPACING.EXACTLY
    pf.line_spacing = LINE
    pf.space_before = Pt(0)
    pf.space_after = AFTER
    if indent:  # 首行缩进 2 字符
        pf.first_line_indent = Pt(32)
        p._p.pPr.find(qn("w:ind")).set(qn("w:firstLineChars"), "200")
    if text:
        _set_font(p.add_run(text), font, size)
    return p


def _table(doc, rows):
    """全框线、居中；表头黑体四号，内容仿宋四号，单倍行距，单元格居中，表后空一行。"""
    t = doc.add_table(rows=len(rows), cols=max(len(r) for r in rows))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, row in enumerate(rows):
        for j, val in enumerate(row):
            c = t.cell(i, j)
            c.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            p = c.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.line_spacing = 1.0
            if val:
                _set_font(p.add_run(str(val)), HT if i == 0 else FS, SI)
    _para(doc, "", FS, SAN, indent=False)


def _page_number(section):
    fp = section.footer.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER

    def run():
        r = fp.add_run()
        r.font.size = Pt(9)
        return r

    b = OxmlElement("w:fldChar"); b.set(qn("w:fldCharType"), "begin"); run()._r.append(b)
    it = OxmlElement("w:instrText"); it.set(qn("xml:space"), "preserve"); it.text = "PAGE   \\* MERGEFORMAT"
    run()._r.append(it)
    s = OxmlElement("w:fldChar"); s.set(qn("w:fldCharType"), "separate"); run()._r.append(s)
    run().text = "1"
    e = OxmlElement("w:fldChar"); e.set(qn("w:fldCharType"), "end"); run()._r.append(e)


def _setup(doc):
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Cm(21), Cm(29.7)
    sec.top_margin = sec.bottom_margin = Cm(2.54)
    sec.left_margin = sec.right_margin = Cm(3.17)
    sec.header_distance, sec.footer_distance = Cm(1.5), Cm(1.75)
    grid = sec._sectPr.find(qn("w:docGrid"))
    if grid is None:
        grid = OxmlElement("w:docGrid")
        sec._sectPr.append(grid)
    grid.set(qn("w:type"), "lines")
    grid.set(qn("w:linePitch"), "312")
    st = doc.styles["Normal"]
    st.font.size = SAN
    rf = st.element.get_or_add_rPr().get_or_add_rFonts()
    for a in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        rf.set(qn(a), FS)
    # 中文排版设置：中文语言、全半角平衡、标点挤压、Word 2013+ 兼容模式
    dflt = doc.styles.element.find(qn("w:docDefaults")).find(qn("w:rPrDefault")).find(qn("w:rPr"))
    lang = dflt.find(qn("w:lang"))
    lang.set(qn("w:eastAsia"), "zh-CN")
    kern = OxmlElement("w:kern")
    kern.set(qn("w:val"), "2")
    lang.addprevious(kern)
    compat = doc.settings.element.find(qn("w:compat"))
    for tag in ["spaceForUL", "balanceSingleByteDoubleByteWidth", "doNotLeaveBackslashAlone",
                "ulTrailSpace", "doNotExpandShiftReturn", "adjustLineHeightInTable"][::-1]:
        compat.insert(0, OxmlElement("w:" + tag))
    csc = doc.settings.element.find(qn("w:characterSpacingControl"))
    if csc is not None:
        csc.set(qn("w:val"), "compressPunctuation")
    for cs in compat.findall(qn("w:compatSetting")):
        if cs.get(qn("w:name")) == "compatibilityMode":
            cs.set(qn("w:val"), "15")
    _page_number(sec)


def build_docx(doc: Document, out: Path) -> Path:
    out = Path(out)
    d = new_docx()
    _setup(d)
    for b in doc.blocks:
        if b.t == "title":
            _para(d, b.text, XBS, ER, "center", indent=False)
    if doc.kind == "brief":
        _para(d, "", FS, SAN, "center", indent=False)
    for b in doc.blocks:
        if b.t in ("title", "attachment", "signer", "date"):
            continue
        if b.t == "table":
            if b.rows:
                _table(d, b.rows)
        else:
            _para(d, b.text, FONTS[b.t], SAN, indent=b.t != "addressee")
    attachments = [b.text for b in doc.blocks if b.t == "attachment"]
    if attachments:
        _para(d, "附件", FS, SAN)
        for i, a in enumerate(attachments, 1):
            _para(d, f"{i}、{a}", FS, SAN)
    signoff = [b for b in doc.blocks if b.t in ("signer", "date")]
    if signoff:
        _para(d, "", FS, SAN, "right", indent=False)
        for b in signoff:
            text = normalize_date(b.text) if b.t == "date" else b.text
            _para(d, text, FS, SAN, "right", indent=False)
    out.parent.mkdir(parents=True, exist_ok=True)
    d.save(str(out))
    return out


def default_filename(doc: Document) -> str:
    title = "".join(b.text for b in doc.blocks if b.t == "title")
    title = re.sub(r'[\\/:*?"<>|\x00-\x1f\x7f]', "", title).strip()
    title = title[:80].rstrip(". ")  # Windows 不允许以点或空格结尾；避免路径过长
    return f"{title or '公文'}.docx"
