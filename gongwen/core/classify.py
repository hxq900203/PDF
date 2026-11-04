"""自动识别段落类型（规则见设计文档 3.3）。"""
import re

from .model import Block, Document

SHORT = 30       # 主送机关最长字数
TITLE_MAX = 40   # 标题第二行最长字数
SIGNER_MAX = 20  # 落款最长字数
H_MAX = 50       # 带序号但超过此长度且以“。”结尾的段落视为正文

_CN = "一二三四五六七八九十"
H1 = re.compile(rf"^[{_CN}]+\s*、")
H2 = re.compile(rf"^[（(][{_CN}]+[）)]")
H3 = re.compile(r"^(?:\d+\s*[、．]|\d+\.(?!\d)|[（(]\d+[）)])\s*")  # 1、 1． 1. （1）；不含 1.5
DATE = re.compile(r"^(?:\d{4}年\d{1,2}月\d{1,2}日|[〇零一二三四五六七八九]{4}年[一二三四五六七八九十]{1,3}月[一二三四五六七八九十]{1,3}日)$")
ATTACH_HEAD = ("附件", "附件：", "附件:")
ATTACH_INLINE = re.compile(r"^附件[：:]\s*(.+)$")
NO_END = tuple("。；，：:！？")


def _numbered(text: str) -> bool:
    return bool(H1.match(text) or H2.match(text) or H3.match(text))


def _heading(text: str) -> str:
    level = "h1" if H1.match(text) else "h2" if H2.match(text) else "h3" if H3.match(text) else None
    if level is None or (len(text) > H_MAX and text.endswith("。")):
        return "body"
    return level


def classify(blocks: list[Block]) -> Document:
    blocks = [Block(b.t, b.text, b.rows) for b in blocks]
    n = len(blocks)
    labels: list[str | None] = ["table" if b.t == "table" else None for b in blocks]
    text_idx = [i for i in range(n) if labels[i] is None]
    if not text_idx:
        return Document("brief", blocks)

    # 标题：第一个非表格段落；紧接的第二段若短、无句末标点、无序号，也是标题
    first = text_idx[0]
    labels[first] = "title"
    last_title = first
    nxt = first + 1
    if nxt < n and labels[nxt] is None:
        t = blocks[nxt].text
        if len(t) <= TITLE_MAX and not t.endswith(NO_END) and not _numbered(t) and not DATE.match(t):
            labels[nxt] = "title"
            last_title = nxt

    # 主送机关：标题后第一段，以冒号结尾、短、不含句号
    k = last_title + 1
    if k < n and labels[k] is None:
        t = blocks[k].text
        if t.endswith(("：", ":")) and len(t) <= SHORT and "。" not in t and t not in ATTACH_HEAD:
            labels[k] = "addressee"

    # 日期：最后一个非表格段落；落款：日期前一段
    last = text_idx[-1]
    if labels[last] is None and DATE.match(blocks[last].text):
        labels[last] = "date"
        s = last - 1
        if s >= 0 and labels[s] is None:
            t = blocks[s].text
            if len(t) <= SIGNER_MAX and not t.endswith(NO_END) and not _numbered(t) and t not in ATTACH_HEAD:
                labels[s] = "signer"

    # 其余：附件区、序号标题、正文
    out: list[Block] = []
    in_attach = False
    for i, b in enumerate(blocks):
        if labels[i] is None:
            t = b.text
            if t in ATTACH_HEAD:
                in_attach = True
                continue  # “附件”行导出时自动生成
            m = ATTACH_INLINE.match(t)
            if m:
                in_attach = False
                b = Block("attachment", m.group(1))
                out.append(b)
                continue
            if in_attach and H3.match(t):
                out.append(Block("attachment", H3.sub("", t, count=1)))
                continue
            in_attach = False
            labels[i] = _heading(t)
        elif labels[i] not in ("table",):
            in_attach = False
        out.append(Block(labels[i], b.text, b.rows))

    kind = "notice" if any(b.t == "addressee" for b in out) else "brief"
    return Document(kind, out)
