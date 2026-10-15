import os
import shutil
import subprocess
import sys
import tempfile
import threading
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


@register("word", "pdf")
@register("excel", "pdf")
def office_to_pdf(src: Path, out_dir: Path, opts: Options) -> list[Path]:
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
