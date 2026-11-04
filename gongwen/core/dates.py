import re

_DIGITS = {"〇": 0, "○": 0, "Ｏ": 0, "０": 0, "零": 0, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
_CN_DATE = re.compile(r"^([〇○Ｏ０零一二三四五六七八九]{4})年([一二三四五六七八九十]{1,3})月([一二三四五六七八九十]{1,3})日$")


def _small(s: str) -> int | None:
    """一 → 1，十 → 10，十二 → 12，二十四 → 24。"""
    if "十" not in s:
        return _DIGITS.get(s) if len(s) == 1 else None
    tens, _, ones = s.partition("十")
    if len(tens) > 1 or len(ones) > 1 or (tens and tens not in _DIGITS) or (ones and ones not in _DIGITS):
        return None
    return (_DIGITS[tens] if tens else 1) * 10 + (_DIGITS[ones] if ones else 0)


def normalize_date(s: str) -> str:
    """中文数字日期转阿拉伯数字（二〇二六年八月二十四日 → 2026年8月24日）；无法解析时原样返回。"""
    m = _CN_DATE.match(s.strip())
    if not m:
        return s
    year = "".join(str(_DIGITS[c]) for c in m.group(1))
    month, day = _small(m.group(2)), _small(m.group(3))
    if month is None or day is None or not 1 <= month <= 12 or not 1 <= day <= 31:
        return s
    return f"{year}年{month}月{day}日"
