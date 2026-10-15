import logging
import os
import sys
from pathlib import Path

APP_NAME = "文件转换器"


def log_dir() -> Path:
    if sys.platform == "win32" and os.environ.get("LOCALAPPDATA"):
        base = Path(os.environ["LOCALAPPDATA"])
    else:
        base = Path.home() / ".local" / "share"
    return base / APP_NAME / "logs"


def setup_logging() -> Path:
    path = log_dir() / "app.log"
    path.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        filename=path, encoding="utf-8", level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    return path
