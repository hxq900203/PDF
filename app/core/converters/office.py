import os
import shutil
import subprocess
import sys
import tempfile
import threading
import zipfile
from pathlib import Path

from ..errors import ConversionError
from ..options import Options
from ..registry import register

TIMEOUT_SECONDS = 120
_lock = threading.Lock()


def app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parents[3]


def find_soffice() -> Path | None:
    candidates = []
    if os.environ.get("FC_SOFFICE"):
        candidates.append(Path(os.environ["FC_SOFFICE"]))
    candidates.append(app_dir() / "libreoffice" / "program" / "soffice.exe")
    which = shutil.which("soffice")
    if which:
        candidates.append(Path(which))
    candidates += [
        Path("C:/Program Files/LibreOffice/program/soffice.exe"),
        Path("C:/Program Files (x86)/LibreOffice/program/soffice.exe"),
    ]
    return next((p for p in candidates if p.is_file()), None)


OLE_MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"


def _check_office_file(src: Path) -> None:
    """在交给 LibreOffice 前排除空文件和改了扩展名的文件（否则会“成功”产出垃圾 PDF）。"""
    try:
        size = src.stat().st_size
        with open(src, "rb") as f:
            head = f.read(8)
    except OSError as e:
        raise ConversionError("文件已损坏或无法读取") from e
    ext = src.suffix.lower()
    if size == 0:
        ok = False
    elif ext in (".docx", ".xlsx"):
        ok = zipfile.is_zipfile(src)
    elif ext == ".doc":  # Word 也会把 RTF/HTML 存成 .doc
        ok = head == OLE_MAGIC or head.startswith(b"{\\rtf") or head.lstrip().lower().startswith(b"<")
    else:  # .xls
        ok = head == OLE_MAGIC or head.lstrip().lower().startswith(b"<")
    if not ok:
        raise ConversionError("文件已损坏或无法读取")


@register("word", "pdf")
@register("excel", "pdf")
def office_to_pdf(src: Path, out_dir: Path, opts: Options) -> list[Path]:
    _check_office_file(src)
    soffice = find_soffice()
    if soffice is None:
        raise ConversionError("未找到 LibreOffice 组件，请重新解压完整的软件包")
    out_dir.mkdir(parents=True, exist_ok=True)
    profile = Path(tempfile.mkdtemp(prefix="fc_lo_"))
    cmd = [str(soffice), "--headless", "--norestore",
           f"-env:UserInstallation={profile.as_uri()}",
           "--convert-to", "pdf", "--outdir", str(out_dir), str(src)]
    flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
    try:
        with _lock:
            result = subprocess.run(cmd, capture_output=True, timeout=TIMEOUT_SECONDS,
                                    creationflags=flags)
    except subprocess.TimeoutExpired as e:
        raise ConversionError(f"转换超时（超过 {TIMEOUT_SECONDS} 秒）") from e
    finally:
        shutil.rmtree(profile, ignore_errors=True)
    path = out_dir / f"{src.stem}.pdf"
    if result.returncode != 0 or not path.is_file():
        raise ConversionError("文件已损坏或无法读取")
    return [path]
