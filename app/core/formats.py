from pathlib import Path

_EXT_TO_FORMAT = {
    ".docx": "word", ".doc": "word",
    ".xlsx": "excel", ".xls": "excel",
    ".png": "image", ".jpg": "image", ".jpeg": "image",
    ".pdf": "pdf",
}

OUTPUT_EXT = {"word": ".docx", "excel": ".xlsx", "pdf": ".pdf", "image": ".png"}

LABELS = {"pdf": "PDF", "word": "Word", "excel": "Excel", "image": "PNG 图片"}


def detect_format(path: Path) -> str | None:
    return _EXT_TO_FORMAT.get(Path(path).suffix.lower())
