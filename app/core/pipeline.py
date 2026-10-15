import shutil
import tempfile
from pathlib import Path

from . import converters  # noqa: F401  确保转换器已注册
from .converters.pdf_image import images_to_single_pdf
from .errors import ConversionError
from .formats import OUTPUT_EXT, detect_format
from .naming import unique_path
from .options import Options
from .registry import DISABLED, find_route


def convert_file(src: Path, target: str, out_dir: Path | None, opts: Options) -> list[Path]:
    src = Path(src)
    fmt = detect_format(src)
    if fmt is None:
        raise ConversionError("不支持的文件格式")
    route = None if (fmt, target) in DISABLED else find_route(fmt, target)
    if not route:
        raise ConversionError("不支持转换为该格式")
    out_dir = Path(out_dir) if out_dir else src.parent

    with tempfile.TemporaryDirectory(prefix="fc_") as tmp:
        current = [src]
        for step, (_, _, convert) in enumerate(route):
            step_dir = Path(tmp) / f"step{step}"
            current = [out for f in current for out in convert(f, step_dir, opts)]

        out_dir.mkdir(parents=True, exist_ok=True)
        ext = OUTPUT_EXT[target]
        if len(current) == 1:
            names = [f"{src.stem}{ext}"]
        else:
            names = [f"{src.stem}_第{i}页{ext}" for i in range(1, len(current) + 1)]
        finals = []
        for produced, name in zip(current, names):
            final = unique_path(out_dir, name)
            shutil.move(produced, final)
            finals.append(final)
    return finals


def merge_images_to_pdf(srcs: list[Path], out_dir: Path | None) -> Path:
    srcs = [Path(s) for s in srcs]
    out_dir = Path(out_dir) if out_dir else srcs[0].parent
    out_dir.mkdir(parents=True, exist_ok=True)
    return images_to_single_pdf(srcs, unique_path(out_dir, f"{srcs[0].stem}_合并.pdf"))
