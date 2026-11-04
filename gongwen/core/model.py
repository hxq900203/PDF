import re
from dataclasses import dataclass

from .errors import GongwenError

TYPES = ("title", "addressee", "h1", "h2", "h3", "body", "attachment", "signer", "date", "table")
KINDS = ("notice", "brief")  # 通知 / 信息简报

_INVALID = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def clean_text(s: str) -> str:
    """去掉 Word（XML）不允许的控制字符。"""
    return _INVALID.sub("", s)


@dataclass
class Block:
    t: str
    text: str = ""
    rows: list[list[str]] | None = None

    def to_dict(self) -> dict:
        if self.t == "table":
            return {"t": "table", "rows": self.rows or []}
        return {"t": self.t, "text": self.text}

    @classmethod
    def from_dict(cls, d: dict) -> "Block":
        t = d.get("t")
        if t not in TYPES:
            raise GongwenError("段落类型无效")
        if t == "table":
            return cls("table", rows=[[clean_text(str(c)) for c in row] for row in d.get("rows") or []])
        return cls(t, clean_text(str(d.get("text", ""))))


@dataclass
class Document:
    kind: str
    blocks: list[Block]

    def to_dict(self) -> dict:
        return {"kind": self.kind, "blocks": [b.to_dict() for b in self.blocks]}

    @classmethod
    def from_dict(cls, d: dict) -> "Document":
        if d.get("kind") not in KINDS:
            raise GongwenError("文种无效")
        return cls(d["kind"], [Block.from_dict(b) for b in d.get("blocks") or []])
