from app.core.naming import unique_path
from app.core.options import Options


def test_unique_path_free(tmp_path):
    assert unique_path(tmp_path, "报告.pdf") == tmp_path / "报告.pdf"


def test_unique_path_collisions(tmp_path):
    (tmp_path / "报告.pdf").touch()
    (tmp_path / "报告 (1).pdf").touch()
    assert unique_path(tmp_path, "报告.pdf") == tmp_path / "报告 (2).pdf"


def test_options_from_dict():
    assert Options.from_dict({"dpi": 300, "merge_images": True, "x": 1}) == Options(300, True)
    assert Options.from_dict({"dpi": 999}).dpi == 200
    assert Options.from_dict({}) == Options()
