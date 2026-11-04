import re
from pathlib import Path

import docx
from docx.oxml.ns import qn
from docx.table import Table

from .errors import GongwenError
from .model import Block, clean_text
from .numbering import Numbering

_SPACES = " \t　\xa0"
_BREAKS = re.compile(r"\r\n|[\r\n\v\f\x85  ]")  # Word 复制出的手动换行常为 \v，分页为 \f
# 这些元素里的文字不属于正文：删除的修订、文本框、兼容回退内容
_SKIP = {qn("w:del"), qn("w:txbxContent"), "{http://schemas.openxmlformats.org/markup-compatibility/2006}Fallback"}


def _clean_lines(text: str) -> list[str]:
    """按换行拆分，去掉控制字符、首尾空格（含全角）和空行；文字内部不改。"""
    lines = (clean_text(line).strip(_SPACES) for line in _BREAKS.split(text))
    return [line for line in lines if line]


def read_text(text: str) -> list[Block]:
    blocks = [Block("body", line) for line in _clean_lines(text)]
    if not blocks:
        raise GongwenError("没有读到任何文字")
    return blocks


def _skipped(el, stop) -> bool:
    while el is not None and el is not stop:
        if el.tag in _SKIP:
            return True
        el = el.getparent()
    return False


def _para_text(p) -> str:
    """段落全部可见文字：含修订插入、域结果、智能标记、内容控件；手动换行和分页符变为换行。"""
    parts = []
    for el in p.iter(qn("w:t"), qn("w:tab"), qn("w:br"), qn("w:cr")):
        if _skipped(el, p):
            continue
        if el.tag == qn("w:t"):
            parts.append(el.text or "")
        elif el.tag == qn("w:tab"):
            parts.append("\t")
        else:
            parts.append("\n")
    return "".join(parts)


def _walk(parent, document, numbering, blocks):
    for el in parent.iterchildren():
        if el.tag == qn("w:p"):
            text = numbering.prefix(el) + _para_text(el)
            blocks += [Block("body", line) for line in _clean_lines(text)]
        elif el.tag == qn("w:tbl"):
            rows = [["\n".join(_clean_lines("\n".join(_para_text(p) for p in c._tc.iter(qn("w:p")))))
                     for c in row.cells] for row in Table(el, document).rows]
            if any(any(c for c in row) for row in rows):
                blocks.append(Block("table", rows=rows))
        elif el.tag == qn("w:sdt"):
            content = el.find(qn("w:sdtContent"))
            if content is not None:
                _walk(content, document, numbering, blocks)
        elif el.tag == qn("w:customXml"):
            _walk(el, document, numbering, blocks)


def read_docx(path: Path) -> list[Block]:
    path = Path(path)
    if path.suffix.lower() == ".doc":
        raise GongwenError("暂不支持老版 .doc 文件，请先用「文件转换器」转为 .docx，或复制文字后点「粘贴文字」")
    try:
        document = docx.Document(str(path))
    except Exception as e:
        raise GongwenError("文件已损坏或无法读取") from e

    blocks: list[Block] = []
    _walk(document.element.body, document, Numbering(document), blocks)
    if not blocks:
        raise GongwenError("没有读到任何文字")
    return blocks
