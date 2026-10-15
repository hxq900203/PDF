import json

import pytest

from app import api as api_mod
from app.api import Api
from app.main import main
from conftest import needs_soffice


class _AnyStr:
    def __eq__(self, other):
        return isinstance(other, str)


ANY_STR = _AnyStr()


class FakeWindow:
    def __init__(self):
        self.calls = []

    def evaluate_js(self, code):
        self.calls.append(code)

    def events(self):
        prefix = "window.onBackendEvent("
        return [json.loads(c[len(prefix):-1]) for c in self.calls if c.startswith(prefix)]


def make_api():
    api, w = Api(), FakeWindow()
    api.attach(w)
    return api, w


def test_get_targets(sample_pdf):
    assert [t["key"] for t in Api().get_targets([str(sample_pdf)])] == ["word", "image", "excel"]
    assert Api().get_targets([str(sample_pdf)])[0] == {"key": "word", "label": "Word"}


def test_describe(sample_pdf, tmp_path):
    txt = tmp_path / "a.txt"
    info = Api().describe([str(sample_pdf), str(txt)])
    assert info[0] == {"path": str(sample_pdf), "name": "中文 样例.pdf", "format": "pdf", "label": "PDF"}
    assert info[1]["format"] is None and info[1]["label"] is None


def test_batch_continues_after_failure(sample_png, corrupt_pdf, tmp_path):
    api, w = make_api()
    api.run_batch([str(corrupt_pdf), str(sample_png)], "pdf", str(tmp_path / "o"), {})
    ev = w.events()
    assert ev[0] == {"type": "status", "index": 0, "state": "running"}
    assert ev[1] == {"type": "status", "index": 0, "state": "error", "message": ANY_STR}
    assert ev[-2]["state"] == "done" and ev[-2]["index"] == 1
    assert ev[-1] == {"type": "finished", "ok": 1, "failed": 1, "out_dir": str(tmp_path / "o")}


def test_unexpected_exception_message(monkeypatch, sample_png, tmp_path):
    def boom(*a):
        raise ValueError("x")
    monkeypatch.setattr(api_mod, "convert_file", boom)
    api, w = make_api()
    api.run_batch([str(sample_png)], "pdf", str(tmp_path), {})
    assert w.events()[1]["message"] == "转换失败：ValueError"
    assert w.events()[-1]["out_dir"] is None


def test_merge_images_batch(sample_png, tmp_path):
    out = tmp_path / "o"
    api, w = make_api()
    api.run_batch([str(sample_png)] * 2, "pdf", str(out), {"merge_images": True})
    assert w.events()[-1]["ok"] == 2 and len(list(out.glob("*.pdf"))) == 1


def test_default_out_dir(sample_png):
    api, w = make_api()
    api.run_batch([str(sample_png)], "pdf", None, {})
    assert w.events()[-1]["out_dir"] == str(sample_png.parent)


@needs_soffice
def test_selftest_ok(monkeypatch, tmp_path):
    log = tmp_path / "selftest.log"
    monkeypatch.setenv("FC_SELFTEST_LOG", str(log))
    assert main(["--selftest"]) == 0
    assert log.read_text(encoding="utf-8") == "OK"


def test_selftest_fail(monkeypatch, tmp_path):
    from app.core.converters import office
    monkeypatch.setattr(office, "find_soffice", lambda: None)
    log = tmp_path / "selftest.log"
    monkeypatch.setenv("FC_SELFTEST_LOG", str(log))
    assert main(["--selftest"]) == 1
    assert "LibreOffice" in log.read_text(encoding="utf-8")


def test_batch_always_finishes(zero_page_pdf, sample_pdf, tmp_path):
    api, w = make_api()
    api.run_batch([str(zero_page_pdf), str(sample_pdf)], "image", str(tmp_path / "o"), {})
    ev = w.events()
    assert ev[1]["state"] == "error"
    assert ev[-1] == {"type": "finished", "ok": 1, "failed": 1, "out_dir": str(tmp_path / "o")}


def test_batch_finishes_when_emit_fails(monkeypatch, sample_png, tmp_path):
    api, w = make_api()
    real = w.evaluate_js
    def flaky(code):
        if '"state": "done"' in code:
            raise RuntimeError("js error")
        real(code)
    w.evaluate_js = flaky
    api.run_batch([str(sample_png)], "pdf", str(tmp_path), {})
    assert w.events()[-1]["type"] == "finished"


def test_merge_with_bad_image(sample_png, tmp_path):
    bad = tmp_path / "坏.png"
    bad.write_bytes(b"not an image")
    out = tmp_path / "o"
    api, w = make_api()
    api.run_batch([str(sample_png), str(bad), str(sample_png)], "pdf", str(out), {"merge_images": True})
    by_index = {e["index"]: e for e in w.events() if e["type"] == "status" and e["state"] != "running"}
    assert by_index[0]["state"] == "done" and by_index[2]["state"] == "done"
    assert by_index[1] == {"type": "status", "index": 1, "state": "error", "message": "文件已损坏或无法读取"}
    (pdf,) = out.glob("*.pdf")
    import pymupdf
    assert pymupdf.open(pdf).page_count == 2
    assert w.events()[-1]["ok"] == 2 and w.events()[-1]["failed"] == 1


def test_log_file_written(monkeypatch, tmp_path):
    import logging
    from app import logging_setup
    monkeypatch.setattr(logging_setup, "log_dir", lambda: tmp_path / "logs")
    path = logging_setup.setup_logging()
    Api._message(RuntimeError("boom"))
    for h in logging.getLogger().handlers:
        h.flush()
    assert "boom" in path.read_text(encoding="utf-8")
