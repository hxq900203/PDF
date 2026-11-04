# PyInstaller 打包配置：pyinstaller build/gongwen.spec --distpath build/dist --workpath build/work
import os

from PyInstaller.utils.hooks import collect_all

ROOT = os.path.abspath(os.path.join(SPECPATH, ".."))

datas = [(os.path.join(ROOT, "gongwen", "web"), os.path.join("gongwen", "web"))]
binaries = []
hiddenimports = []
for pkg in ("webview", "docx"):
    d, b, h = collect_all(pkg)
    datas += d
    binaries += b
    hiddenimports += h

a = Analysis(
    [os.path.join(ROOT, "gongwen", "main.py")],
    pathex=[ROOT],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=["app", "pymupdf", "fitz", "pdf2docx", "pdfplumber", "openpyxl"],
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="公文排版", console=False)
coll = COLLECT(exe, a.binaries, a.datas, name="公文排版")
