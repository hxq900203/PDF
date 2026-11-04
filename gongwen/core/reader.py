import re
from pathlib import Path

import docx
from docx.oxml.ns import qn
from docx.table import Table
from docx.text.paragraph import Paragraph

from .errors import GongwenError
from .model import Block

_SPACES = " \t　\xa0"


def _clean_lines(text: str) -> list[str]:
    """按换行拆分，去掉首尾空格（含全角）和空行；文字内部不改。"""
    lines = (line.strip(_SPACES) for line in re.split(r"\r\n|\r|\n", text))
    return [line for line in lines if line]


def read_text(text: str) -> list[Block]:
    blocks = [Block("body", line) for line in _clean_lines(text)]
    if not blocks:
        raise GongwenError("没有读到任何文字")
    return blocks


def read_docx(path: Path) -> list[Block]:
    path = Path(path)
    if path.suffix.lower() == ".doc":
        raise GongwenError("暂不支持老版 .doc 文件，请先用「文件转换器」转为 .docx，或复制文字后点「粘贴文字」")
    try:
        document = docx.Document(str(path))
    except Exception as e:
        raise GongwenError("文件已损坏或无法读取") from e

    blocks = []
    for el in document.element.body.iterchildren():
        if el.tag == qn("w:p"):
            # 段落内的手动换行（Shift+Enter）在 text 中是 \n，拆成多段
            blocks += [Block("body", line) for line in _clean_lines(Paragraph(el, document).text)]
        elif el.tag == qn("w:tbl"):
            rows = [[c.text.strip(_SPACES) for c in row.cells] for row in Table(el, document).rows]
            if any(any(c for c in row) for row in rows):
                blocks.append(Block("table", rows=rows))
    if not blocks:
        raise GongwenError("没有读到任何文字")
    return blocks
