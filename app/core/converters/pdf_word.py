import logging
from pathlib import Path

from pdf2docx import Converter

from ..errors import ConversionError
from ..options import Options
from ..registry import register
from .pdf_image import open_pdf


@register("pdf", "word")
def pdf_to_word(src: Path, out_dir: Path, opts: Options) -> list[Path]:
    open_pdf(src).close()  # 先检查加密/损坏，给出中文提示
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{src.stem}.docx"
    logging.getLogger("pdf2docx").setLevel(logging.WARNING)
    cv = Converter(str(src))
    try:
        cv.convert(str(path))
    except Exception as e:
        raise ConversionError("PDF 转 Word 失败，文件可能已损坏") from e
    finally:
        cv.close()
    return [path]
