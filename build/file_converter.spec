# PyInstaller 打包配置：pyinstaller build/file_converter.spec --distpath build/dist --workpath build/work
import os

from PyInstaller.utils.hooks import collect_all

ROOT = os.path.abspath(os.path.join(SPECPATH, ".."))

datas = [(os.path.join(ROOT, "app", "web"), os.path.join("app", "web"))]
binaries = []
hiddenimports = []
for pkg in ("webview", "pdf2docx", "pdfplumber", "pymupdf"):
    d, b, h = collect_all(pkg)
    datas += d
    binaries += b
    hiddenimports += h

a = Analysis(
    [os.path.join(ROOT, "app", "main.py")],
    pathex=[ROOT],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="文件转换器",
    console=False,
)
coll = COLLECT(exe, a.binaries, a.datas, name="文件转换器")
