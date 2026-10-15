import json
import logging
import os
import subprocess
import sys
import threading
from pathlib import Path

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
        ok = failed = 0
        first_dir = None

        if target == "pdf" and opts.merge_images and paths and \
                all(detect_format(Path(p)) == "image" for p in paths):
            for i in range(len(paths)):
                self._emit({"type": "status", "index": i, "state": "running"})
            try:
                merged = merge_images_to_pdf([Path(p) for p in paths], out)
                states = [{"state": "done", "outputs": [str(merged)]}] * len(paths)
                ok, first_dir = len(paths), str(merged.parent)
            except Exception as e:
                states = [{"state": "error", "message": self._message(e)}] * len(paths)
                failed = len(paths)
            for i, s in enumerate(states):
                self._emit({"type": "status", "index": i, **s})
        else:
            for i, p in enumerate(paths):
                self._emit({"type": "status", "index": i, "state": "running"})
                try:
                    outputs = convert_file(Path(p), target, out, opts)
                except Exception as e:
                    failed += 1
                    self._emit({"type": "status", "index": i, "state": "error",
                                "message": self._message(e)})
                    continue
                ok += 1
                first_dir = first_dir or str(outputs[0].parent)
                self._emit({"type": "status", "index": i, "state": "done",
                            "outputs": [str(o) for o in outputs]})

        self._emit({"type": "finished", "ok": ok, "failed": failed, "out_dir": first_dir})

    @staticmethod
    def _message(e: Exception) -> str:
        if isinstance(e, ConversionError):
            return str(e)
        log.exception("未预期的转换错误")
        return f"转换失败：{type(e).__name__}"

    def _emit(self, event: dict) -> None:
        if self._window is not None:
            self._window.evaluate_js(
                f"window.onBackendEvent({json.dumps(event, ensure_ascii=False)})")
