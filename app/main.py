import json
import os
import sys
import tempfile
from pathlib import Path

if __package__ in (None, ""):  # PyInstaller 以脚本方式运行入口
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.api import Api  # noqa: E402
from app.core.converters.office import app_dir  # noqa: E402
from app.core.options import Options  # noqa: E402
from app.core.pipeline import convert_file  # noqa: E402
from app.logging_setup import APP_NAME, setup_logging  # noqa: E402


def web_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / "app" / "web"
    return Path(__file__).resolve().parent / "web"


def selftest() -> int:
    """打包后自检：生成 docx 并转为 PDF，验证内置 LibreOffice 可用。"""
    import docx

    log = Path(os.environ.get("FC_SELFTEST_LOG") or app_dir() / "selftest.log")
    try:
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "自检.docx"
            d = docx.Document()
            d.add_paragraph("自检")
            d.save(src)
            (pdf,) = convert_file(src, "pdf", Path(tmp) / "out", Options())
            assert pdf.stat().st_size > 0
        log.write_text("OK", encoding="utf-8")
        return 0
    except Exception as e:
        log.write_text(f"FAIL: {type(e).__name__}: {e}", encoding="utf-8")
        return 1


def run_gui() -> None:
    import webview
    from webview.dom import DOMEventHandler

    setup_logging()
    api = Api()
    window = webview.create_window(APP_NAME, url=str(web_dir() / "index.html"), js_api=api,
                                   width=900, height=680, min_size=(720, 520))
    api.attach(window)

    def on_drop(event):
        files = event.get("dataTransfer", {}).get("files", [])
        paths = [f["pywebviewFullPath"] for f in files if f.get("pywebviewFullPath")]
        if paths:
            window.evaluate_js(f"window.addFiles({json.dumps(paths, ensure_ascii=False)})")

    def on_loaded():
        events = window.dom.document.events
        events.dragover += DOMEventHandler(lambda e: None, prevent_default=True, stop_propagation=True)
        events.drop += DOMEventHandler(on_drop, prevent_default=True, stop_propagation=True)

    window.events.loaded += on_loaded
    webview.start()


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if "--selftest" in argv:
        return selftest()
    run_gui()
    return 0


if __name__ == "__main__":
    sys.exit(main())
