import logging
import os
import subprocess
import sys
from pathlib import Path

from .core.build import build_docx, default_filename
from .core.classify import classify
from .core.errors import GongwenError
from .core.model import Document
from .core.reader import read_docx, read_text

log = logging.getLogger(__name__)


class Api:
    """供界面 JS 调用（window.pywebview.api.*）；所有方法返回 dict，不向 JS 抛异常。"""

    def __init__(self):
        self._window = None

    def attach(self, window) -> None:
        self._window = window

    def open_docx(self, path: str) -> dict:
        try:
            return {"doc": classify(read_docx(Path(path))).to_dict()}
        except Exception as e:
            return {"error": self._message(e)}

    def parse_text(self, text: str) -> dict:
        try:
            return {"doc": classify(read_text(text or "")).to_dict()}
        except Exception as e:
            return {"error": self._message(e)}

    def pick_docx(self) -> str | None:
        import webview
        result = self._window.create_file_dialog(
            webview.FileDialog.OPEN, file_types=("Word 文档 (*.docx;*.doc)",))
        return result[0] if result else None

    def export(self, doc: dict) -> dict:
        try:
            name = default_filename(Document.from_dict(doc))
        except Exception as e:
            return {"error": self._message(e)}
        import webview
        result = self._window.create_file_dialog(
            webview.FileDialog.SAVE, save_filename=name, file_types=("Word 文档 (*.docx)",))
        if isinstance(result, (list, tuple)):
            result = result[0] if result else None
        if not result:
            return {"cancelled": True}
        path = Path(result)
        if path.suffix.lower() != ".docx":
            path = path.with_name(path.name + ".docx")
        return self.export_to(doc, str(path))

    def export_to(self, doc: dict, path: str) -> dict:
        try:
            return {"path": str(build_docx(Document.from_dict(doc), Path(path)))}
        except PermissionError:
            return {"error": "文件正在被其他程序使用，请先关闭它或换个文件名"}
        except Exception as e:
            return {"error": self._message(e)}

    def open_file(self, path: str) -> None:
        if sys.platform == "win32":
            os.startfile(path)  # noqa: S606
        else:
            subprocess.Popen(["xdg-open", path])

    @staticmethod
    def _message(e: Exception) -> str:
        if isinstance(e, GongwenError):
            return str(e)
        log.error("未预期的错误", exc_info=e)
        return f"操作失败：{type(e).__name__}"
