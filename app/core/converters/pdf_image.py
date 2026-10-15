from pathlib import Path

import pymupdf

from ..errors import ConversionError
from ..options import Options
from ..registry import register


def open_pdf(path: Path) -> pymupdf.Document:
    """打开 PDF；损坏或加密时抛出带中文提示的 ConversionError。"""
    try:
        doc = pymupdf.open(path, filetype="pdf")
    except Exception as e:
        raise ConversionError("文件已损坏或无法读取") from e
    if doc.needs_pass:
        doc.close()
        raise ConversionError("PDF 已加密，无法转换")
    return doc


def _open_image(path: Path) -> pymupdf.Document:
    try:
        img = pymupdf.open(path)
        pdf_bytes = img.convert_to_pdf()
        img.close()
        return pymupdf.open("pdf", pdf_bytes)
    except Exception as e:
        raise ConversionError("文件已损坏或无法读取") from e


def check_image(path: Path) -> None:
    """图片无法读取时抛出 ConversionError。"""
    _open_image(path).close()


@register("pdf", "image")
def pdf_to_image(src: Path, out_dir: Path, opts: Options) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    zoom = opts.dpi / 72
    outputs = []
    with open_pdf(src) as doc:
        for i, page in enumerate(doc, start=1):
            path = out_dir / f"page_{i:04d}.png"
            page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom)).save(path)
            outputs.append(path)
    return outputs


@register("image", "pdf")
def image_to_pdf(src: Path, out_dir: Path, opts: Options) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{src.stem}.pdf"
    with _open_image(src) as doc:
        doc.save(path)
    return [path]


def images_to_single_pdf(srcs: list[Path], out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with pymupdf.open() as merged:
        for src in srcs:
            with _open_image(src) as doc:
                merged.insert_pdf(doc)
        merged.save(out_path)
    return out_path
