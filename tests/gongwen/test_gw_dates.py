import pytest

from gongwen.core.dates import normalize_date


@pytest.mark.parametrize("src,dst", [
    ("二〇二六年八月二十四日", "2026年8月24日"),
    ("二〇二六年十月一日", "2026年10月1日"),
    ("二零二六年十二月三十一日", "2026年12月31日"),
    ("2026年8月24日", "2026年8月24日"),
    ("二〇二六年十三月一日", "二〇二六年十三月一日"),
    ("二〇二六年二月三十二日", "二〇二六年二月三十二日"),
    ("八月", "八月"),
])
def test_normalize_date(src, dst):
    assert normalize_date(src) == dst
