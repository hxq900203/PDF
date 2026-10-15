import json
import logging
import os
import subprocess
import sys
import threading
from pathlib import Path

from .core.converters.pdf_image import check_image
from .core.errors import ConversionError
from .core.formats import LABELS, detect_format
from .core.options import Options
from .core.pipeline import convert_file, merge_images_to_pdf
from .core.registry import available_targets

log = logging.getLogger(__name__)

FILE_TYPES = ("支持的文件 (*.pdf;*.docx;*.doc;*.xlsx;*.xls;*.png;*.jpg;*.jpeg)",)


class Api:
    """供界面 JS 调用的方法（window.pywebview.api.*）。"""

    def __init__(self):
        self._window = None

    def attach(self, window) -> None:
        self._window = window

    def describe(self, paths: list[str]) -> list[dict]:
        result = []
        for p in paths:
            fmt = detect_format(Path(p))
            result.append({"path": p, "name": Path(p).name, "format": fmt,
                           "label": LABELS.get(fmt) if fmt else None})
        return result

    def get_targets(self, paths: list[str]) -> list[dict]:
        return [{"key": t, "label": LABELS[t]}
                for t in available_targets([Path(p) for p in paths])]

    def pick_files(self) -> list[str]:
        import webview
        result = self._window.create_file_dialog(
            webview.FileDialog.OPEN, allow_multiple=True, file_types=FILE_TYPES)
        return list(result or [])

    def pick_folder(self) -> str | None:
        import webview
        result = self._window.create_file_dialog(webview.FileDialog.FOLDER)
        return result[0] if result else None

    def open_folder(self, path: str) -> None:
        if sys.platform == "win32":
            os.startfile(path)  # noqa: S606
        else:
            subprocess.Popen(["xdg-open", path])

    def start(self, paths: list[str], target: str, out_dir: str | None, options: dict) -> None:
        threading.Thread(target=self.run_batch, args=(paths, target, out_dir, options),
                         daemon=True).start()

    def run_batch(self, paths: list[str], target: str, out_dir: str | None, options: dict) -> None:
        opts = Options.from_dict(options or {})
        out = Path(out_dir) if out_dir else None
        self._ok = self._failed = 0
        self._first_dir = None
        try:
            if target == "pdf" and opts.merge_images and paths and \
                    all(detect_format(Path(p)) == "image" for p in paths):
                self._run_merge(paths, out)
            else:
                for i, p in enumerate(paths):
                    self._run_one(i, Path(p), target, out, opts)
        except Exception:
            log.exception("批次执行异常")
        finally:
            self._emit({"type": "finished", "ok": self._ok, "failed": self._failed,
                        "out_dir": self._first_dir})

    def _run_one(self, i: int, src: Path, target: str, out: Path | None, opts: Options) -> None:
        self._emit({"type": "status", "index": i, "state": "running"})
        try:
            outputs = convert_file(src, target, out, opts)
        except Exception as e:
            self._failed += 1
            self._emit({"type": "status", "index": i, "state": "error", "message": self._message(e)})
            return
        self._ok += 1
        self._first_dir = self._first_dir or str(outputs[0].parent)
        self._emit({"type": "status", "index": i, "state": "done",
                    "outputs": [str(o) for o in outputs]})

    def _run_merge(self, paths: list[str], out: Path | None) -> None:
        good = []
        for i, p in enumerate(paths):
            self._emit({"type": "status", "index": i, "state": "running"})
            try:
                check_image(Path(p))
                good.append(i)
            except Exception as e:
                self._failed += 1
                self._emit({"type": "status", "index": i, "state": "error", "message": self._message(e)})
        if not good:
            return
        try:
            merged = merge_images_to_pdf([Path(paths[i]) for i in good], out)
        except Exception as e:
            self._failed += len(good)
            for i in good:
                self._emit({"type": "status", "index": i, "state": "error", "message": self._message(e)})
            return
        self._ok += len(good)
        self._first_dir = str(merged.parent)
        for i in good:
            self._emit({"type": "status", "index": i, "state": "done", "outputs": [str(merged)]})

    @staticmethod
    def _message(e: Exception) -> str:
        if isinstance(e, ConversionError):
            return str(e)
        log.error("未预期的转换错误", exc_info=e)
        return f"转换失败：{type(e).__name__}"

    def _emit(self, event: dict) -> None:
        if self._window is None:
            return
        try:
            self._window.evaluate_js(
                f"window.onBackendEvent({json.dumps(event, ensure_ascii=False)})")
        except Exception:
            log.exception("推送界面事件失败")
