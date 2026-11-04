from samples import BRIEF, NOTICE

from gongwen.core.classify import classify
from gongwen.core.model import Block
from gongwen.core.reader import read_text


def types(text):
    return [b.t for b in classify(read_text(text)).blocks]


def test_notice_end_to_end():
    d = classify(read_text(NOTICE))
    assert d.kind == "notice"
    assert [b.t for b in d.blocks] == ["title", "title", "addressee", "body", "h1", "h2", "h3", "body",
                                       "attachment", "attachment", "signer", "date"]
    assert d.blocks[8].text == "《罪犯再犯风险评估量表（成年男犯）》及填写说明"
    assert d.blocks[9].text == "《评估报告模板》"
    assert d.blocks[11].text == "二〇二六年八月二十四日"


def test_brief():
    d = classify(read_text(BRIEF))
    assert d.kind == "brief"
    assert [b.t for b in d.blocks] == ["title", "body", "h1", "body"]


def test_long_numbered_is_body():
    long = "一、" + "各监区要高度重视，" * 6 + "确保工作落实到位。"
    assert len(long) > 50
    assert types(f"标题\n{long}") == ["title", "body"]


def test_second_line_with_period_not_title():
    assert types("标题\n这是第一句话。") == ["title", "body"]


def test_second_line_numbered_not_title():
    assert types("标题\n一、总体要求") == ["title", "h1"]


def test_inline_attachment():
    d = classify(read_text("标题\n正文。\n附件：《评估报告模板》"))
    assert [(b.t, b.text) for b in d.blocks][-1] == ("attachment", "《评估报告模板》")


def test_attachment_zone_ends():
    assert types("标题\n正文。\n附件\n（1）《甲》\n特此通知。") == ["title", "body", "attachment", "body"]


def test_irregular_numbering():
    assert types("标题\n　　一 、甲\n(一)乙\n（二)丙\n1．丁\n（1）戊") == ["title", "h1", "h2", "h2", "h3", "h3"]


def test_yishi_is_body():
    assert types("标题\n一是加强领导。") == ["title", "body"]


def test_table_first_and_single_line():
    d = classify([Block("table", rows=[["a"]]), Block("body", "标题")])
    assert [b.t for b in d.blocks] == ["table", "title"]
    assert types("只有一行") == ["title"]


def test_signer_requires_date():
    assert types("标题\n正文。\n评估矫治中心") == ["title", "body", "body"]


def test_arabic_date_and_signer():
    assert types("标题\n正文。\n评估矫治中心\n2026年8月24日") == ["title", "body", "signer", "date"]


def test_addressee_rules():
    assert types("标题\n各监区：")[1] == "addressee"
    assert types("标题\n具体通知如下：为做好工作。现通知：")[1] != "addressee"


def test_decimal_not_heading():
    assert types("标题\n1.5万人参加了活动。") == ["title", "body"]
