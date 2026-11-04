import logging
from pathlib import Path

import docx
from samples import NOTICE

from gongwen import api as api_mod
from gongwen import logging_setup
from gongwen.api import Api
from gongwen.main import main


def doc_dict():
    return Api().parse_text(NOTICE)["doc"]


def raise_(exc):
    def f(*a, **k):
        raise exc
    return f


def test_parse_text():
    d = doc_dict()
    assert d["kind"] == "notice" and d["blocks"][0] == {"t": "title", "text": "关于组织学习临释罪犯再犯风险评估"}


def test_parse_text_empty():
    assert Api().parse_text("  ") == {"error": "没有读到任何文字"}


def test_open_docx(tmp_path):
    d = docx.Document()
    d.add_paragraph("标题")
    d.add_paragraph("正文。")
    p = tmp_path / "样例.docx"
    d.save(p)
    assert [b["t"] for b in Api().open_docx(str(p))["doc"]["blocks"]] == ["title", "body"]


def test_open_docx_error(tmp_path):
    bad = tmp_path / "坏.docx"
    bad.write_bytes(b"x")
    assert "已损坏" in Api().open_docx(str(bad))["error"]


def test_export_to(tmp_path):
    r = Api().export_to(doc_dict(), str(tmp_path / "通知.docx"))
    assert Path(r["path"]).is_file()


def test_export_permission(monkeypatch, tmp_path):
    monkeypatch.setattr(api_mod, "build_docx", raise_(PermissionError()))
    assert Api().export_to(doc_dict(), str(tmp_path / "a.docx")) == {"error": "文件正在被其他程序使用，请先关闭它或换个文件名"}


def test_export_unexpected(monkeypatch, tmp_path):
    monkeypatch.setattr(api_mod, "build_docx", raise_(ValueError("x")))
    assert Api().export_to(doc_dict(), str(tmp_path / "a.docx")) == {"error": "操作失败：ValueError"}


def test_invalid_doc_dict(tmp_path):
    assert Api().export_to({"kind": "x", "blocks": []}, str(tmp_path / "a.docx")) == {"error": "文种无效"}


class FakeWindow:
    def __init__(self, result):
        self.result, self.kwargs = result, None

    def create_file_dialog(self, *a, **k):
        self.kwargs = k
        return self.result


def test_export_dialog(tmp_path):
    api = Api()
    w = FakeWindow(str(tmp_path / "x.docx"))
    api.attach(w)
    assert Path(api.export(doc_dict())["path"]).is_file()
    assert w.kwargs["save_filename"] == "关于组织学习临释罪犯再犯风险评估相关内容的通知.docx"
    api.attach(FakeWindow(None))
    assert api.export(doc_dict()) == {"cancelled": True}


def test_export_dialog_adds_suffix(tmp_path):
    api = Api()
    api.attach(FakeWindow((str(tmp_path / "无后缀"),)))
    assert api.export(doc_dict())["path"].endswith("无后缀.docx")


def test_log_written(monkeypatch, tmp_path):
    monkeypatch.setattr(logging_setup, "log_dir", lambda: tmp_path / "logs")
    path = logging_setup.setup_logging()
    Api._message(RuntimeError("boom"))
    for h in logging.getLogger().handlers:
        h.flush()
    assert "boom" in path.read_text(encoding="utf-8")


def test_selftest(monkeypatch, tmp_path):
    log = tmp_path / "selftest.log"
    monkeypatch.setenv("GW_SELFTEST_LOG", str(log))
    assert main(["--selftest"]) == 0
    assert log.read_text(encoding="utf-8") == "OK"
