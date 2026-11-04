import pytest

from gongwen.core.errors import GongwenError
from gongwen.core.model import KINDS, TYPES, Block, Document


def test_constants():
    assert TYPES == ("title", "addressee", "h1", "h2", "h3", "body", "attachment", "signer", "date", "table")
    assert KINDS == ("notice", "brief")


def test_roundtrip():
    d = Document("notice", [Block("title", "关于…"), Block("table", rows=[["a", "b"]])])
    assert Document.from_dict(d.to_dict()) == d
    assert d.to_dict()["blocks"][0] == {"t": "title", "text": "关于…"}
    assert d.to_dict()["blocks"][1] == {"t": "table", "rows": [["a", "b"]]}


def test_invalid_type():
    with pytest.raises(GongwenError):
        Block.from_dict({"t": "xx", "text": ""})


def test_invalid_kind():
    with pytest.raises(GongwenError):
        Document.from_dict({"kind": "x", "blocks": []})
