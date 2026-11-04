import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WEB = ROOT / "gongwen-web"


def run_build(src_root: Path, out: Path):
    return subprocess.run([sys.executable, str(src_root / "build.py"), "--out", str(out)],
                          capture_output=True, text=True)


def test_build_single_file(tmp_path):
    out = tmp_path / "公文排版.html"
    r = run_build(WEB, out)
    assert r.returncode == 0, r.stderr
    html = out.read_text(encoding="utf-8")
    assert "<script>" in html and "JSZip v3.10.1" in html
    assert " src=" not in html and " href=" not in html


def test_build_rejects_modern_syntax(tmp_path):
    copy = tmp_path / "web"
    shutil.copytree(WEB, copy, ignore=shutil.ignore_patterns("node_modules", "dist"))
    (copy / "src" / "dates.js").write_text("var GW = GW || {};\nvar x = a?.b;\n", encoding="utf-8")
    r = run_build(copy, tmp_path / "x.html")
    assert r.returncode == 1 and "dates.js" in r.stdout + r.stderr
