"""把 Word 自动编号（w:numPr）还原成文字前缀，如“一、”“（一）”“1.”。"""
from docx.oxml.ns import qn

_CN = "零一二三四五六七八九"
_CIRCLED = "①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳"


def _chinese(n: int) -> str:
    if n < 10:
        return _CN[n]
    if n < 100:
        tens, ones = divmod(n, 10)
        return ("" if tens == 1 else _CN[tens]) + "十" + (_CN[ones] if ones else "")
    return str(n)


def _letters(n: int) -> str:
    s = ""
    while n > 0:
        n, r = divmod(n - 1, 26)
        s = chr(97 + r) + s
    return s


def format_number(n: int, fmt: str) -> str:
    if fmt in ("chineseCounting", "chineseCountingThousand", "chineseLegalSimplified", "ideographTraditional",
               "taiwaneseCounting", "taiwaneseCountingThousand"):
        return _chinese(n)
    if fmt == "decimalEnclosedCircle" or fmt == "decimalEnclosedCircleChinese":
        return _CIRCLED[n - 1] if 1 <= n <= len(_CIRCLED) else str(n)
    if fmt == "decimalFullWidth" or fmt == "decimalFullWidth2":
        return "".join(chr(ord(c) + 0xFEE0) for c in str(n))
    if fmt == "lowerLetter":
        return _letters(n)
    if fmt == "upperLetter":
        return _letters(n).upper()
    if fmt in ("bullet", "none"):
        return ""
    return str(n)  # decimal 及未知格式


class Numbering:
    def __init__(self, document):
        self._nums, self._abstract = {}, {}
        try:
            root = document.part.numbering_part.element
        except Exception:  # 文档没有编号定义
            root = None
        if root is not None:
            for a in root.findall(qn("w:abstractNum")):
                self._abstract[a.get(qn("w:abstractNumId"))] = a
            for n in root.findall(qn("w:num")):
                aid = n.find(qn("w:abstractNumId"))
                starts = {}
                for ov in n.findall(qn("w:lvlOverride")):
                    so = ov.find(qn("w:startOverride"))
                    if so is not None:
                        starts[ov.get(qn("w:ilvl"))] = int(so.get(qn("w:val")))
                if aid is not None:
                    self._nums[n.get(qn("w:numId"))] = (aid.get(qn("w:val")), starts)
        self._styles = document.styles.element
        self._counters: dict[str, list[int | None]] = {}

    def _style_numpr(self, style_id):
        seen = set()
        while style_id and style_id not in seen:
            seen.add(style_id)
            style = self._styles.find(f"{qn('w:style')}[@{qn('w:styleId')}='{style_id}']")
            if style is None:
                return None
            ppr = style.find(qn("w:pPr"))
            numpr = ppr.find(qn("w:numPr")) if ppr is not None else None
            if numpr is not None:
                return numpr
            based = style.find(qn("w:basedOn"))
            style_id = based.get(qn("w:val")) if based is not None else None
        return None

    def prefix(self, p) -> str:
        ppr = p.find(qn("w:pPr"))
        numpr = ppr.find(qn("w:numPr")) if ppr is not None else None
        if numpr is None and ppr is not None:
            ps = ppr.find(qn("w:pStyle"))
            numpr = self._style_numpr(ps.get(qn("w:val"))) if ps is not None else None
        if numpr is None:
            return ""
        nid_el, ilvl_el = numpr.find(qn("w:numId")), numpr.find(qn("w:ilvl"))
        num_id = nid_el.get(qn("w:val")) if nid_el is not None else None
        ilvl = int(ilvl_el.get(qn("w:val"))) if ilvl_el is not None else 0
        if num_id not in self._nums:  # numId="0" 表示取消编号
            return ""
        aid, starts = self._nums[num_id]
        abstract = self._abstract.get(aid)
        if abstract is None:
            return ""
        levels = {int(l.get(qn("w:ilvl"))): l for l in abstract.findall(qn("w:lvl"))}
        lvl = levels.get(ilvl)
        if lvl is None:
            return ""

        def val(el, tag, default=None):
            x = el.find(qn(tag))
            return x.get(qn("w:val")) if x is not None else default

        counters = self._counters.setdefault(num_id, [None] * 9)
        start = starts.get(str(ilvl), int(val(lvl, "w:start", "1")))
        counters[ilvl] = start if counters[ilvl] is None else counters[ilvl] + 1
        for deeper in range(ilvl + 1, 9):
            counters[deeper] = None
        text = val(lvl, "w:lvlText", "")
        for k in range(9):
            if f"%{k + 1}" in text:
                l = levels.get(k)
                n = counters[k] if counters[k] is not None else int(val(l, "w:start", "1")) if l is not None else 1
                fmt = val(l, "w:numFmt", "decimal") if l is not None else "decimal"
                text = text.replace(f"%{k + 1}", format_number(n, fmt))
        return text
