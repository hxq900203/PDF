import pytest
from samples import BRIEF, NOTICE

from gongwen.core.classify import classify
from gongwen.core.reader import read_text

TEXTS = [
    NOTICE, BRIEF,
    "标题\n这是第一句话。", "标题\n一、总体要求", "标题\n正文。\n附件：《评估报告模板》",
    "标题\n正文。\n附件\n（1）《甲》\n特此通知。", "标题\n　　一 、甲\n(一)乙\n（二)丙\n1．丁\n（1）戊",
    "只有一行", "标题\n正文。\n评估矫治中心\n2026年8月24日", "标题\n1.5万人参加了活动。",
    "标题\n正文。\n附件：1.《量表》\n2.《说明》", "标题\n正文。\n附件：\n《量表》",
    "标题\n正文。\n评估矫治中心\n二○二六年八月二十四日", "标题\x0b第二行\x0c正文\x07内容。",
]


@pytest.mark.parametrize("text", TEXTS)
def test_same_as_python(js, tmp_path, text):
    f = tmp_path / "in.txt"
    f.write_text(text, encoding="utf-8")
    assert js("classify", f) == classify(read_text(text)).to_dict()
