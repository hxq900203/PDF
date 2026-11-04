import json
import os
import sys
import tempfile
from pathlib import Path

if __package__ in (None, ""):  # PyInstaller 以脚本方式运行入口
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from gongwen.api import Api  # noqa: E402
from gongwen.core.build import XBS, build_docx  # noqa: E402
from gongwen.core.classify import classify  # noqa: E402
from gongwen.core.reader import read_text  # noqa: E402
from gongwen.logging_setup import APP_NAME, setup_logging  # noqa: E402

SAMPLE = "关于开展自检的通知\n各部门：\n一、自检内容\n请按要求完成自检。\n办公室\n2026年8月24日"


def app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent


def web_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / "gongwen" / "web"
    return Path(__file__).resolve().parent / "web"


def selftest() -> int:
    """打包后自检：加载 pythonnet（界面依赖），并把示例文字排版导出、读回检查。"""
    import docx
    from docx.oxml.ns import qn

    log = Path(os.environ.get("GW_SELFTEST_LOG") or app_dir() / "selftest.log")
    try:
        if sys.platform == "win32":
            import clr  # noqa: F401
        with tempfile.TemporaryDirectory() as tmp:
            out = build_docx(classify(read_text(SAMPLE)), Path(tmp) / "自检.docx")
            first = docx.Document(str(out)).paragraphs[0].runs[0]
            assert first._element.rPr.rFonts.get(qn("w:eastAsia")) == XBS
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
                                   width=1200, height=760, min_size=(960, 600))
    api.attach(window)

    def on_drop(event):
        files = event.get("dataTransfer", {}).get("files", [])
        paths = [f["pywebviewFullPath"] for f in files if f.get("pywebviewFullPath")]
        if paths:
            window.evaluate_js(f"window.loadPath({json.dumps(paths[0], ensure_ascii=False)})")

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
