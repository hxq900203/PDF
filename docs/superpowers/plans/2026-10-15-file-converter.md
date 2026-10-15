# 文件格式转换器 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Windows 桌面软件，在 Word / PDF / PNG / Excel 之间转换，LibreOffice 随包，解压即用。

**Architecture:** `app/core/` 是与界面无关的转换核心：转换器登记为有向图的边，BFS 求路径，`pipeline` 在临时目录逐步执行并给最终文件命名。`app/api.py` 是 pywebview 的 JS↔Python 桥，后台线程跑批次并推送状态；`app/web/` 是无框架单页界面。GitHub Actions 在 Windows 上用 PyInstaller 打包并塞入解包后的 LibreOffice。

**Tech Stack:** Python 3.12（本地 3.13 也可），pywebview ≥5，PyMuPDF，pdf2docx，pdfplumber，openpyxl，python-docx（测试/自检生成样例），pytest，PyInstaller。

**Spec:** `docs/superpowers/specs/2026-10-15-file-converter-design.md`

## Global Constraints

- 格式键固定为 `"word" | "excel" | "pdf" | "image"`；扩展名：word = .docx/.doc，excel = .xlsx/.xls，image = .png/.jpg/.jpeg，pdf = .pdf；**大小写不敏感**。
- 各格式的输出扩展名：word → `.docx`，excel → `.xlsx`，pdf → `.pdf`，image → `.png`。
- 界面不提供的组合：image→word、image→excel、word→excel、excel→word（第二版）。
- 绝不覆盖已有文件：重名时 `报告 (1).pdf`、`报告 (2).pdf`……
- 多页图片命名：`原名_第1页.png`、`原名_第2页.png`（页码从 1 起，不补零）。
- DPI 选项：150 / 200 / 300，默认 200。
- LibreOffice：串行（全局锁），每文件超时 120 秒，`-env:UserInstallation` 用临时目录。
- 所有面向用户的错误信息为中文，通过 `ConversionError(message)` 抛出。
- 日志：`%LOCALAPPDATA%/文件转换器/logs/app.log`（非 Windows 时用 `~/.local/share/文件转换器/logs/app.log`）。
- 输出默认目录：源文件所在目录；用户可指定一个统一目录。
- 发布产物：`文件转换器-windows.zip`，内含 `文件转换器/文件转换器.exe` 与 `文件转换器/libreoffice/`。

## Review Focus

1. **中文/带空格的路径和文件名**（`D:\我的 文档\报告 1.docx`）→ 每个转换器都能正常转换。各转换器测试的样例文件名一律用 `中文 样例.xxx`。
2. **损坏或伪装的文件**（0 字节 .pdf、改了扩展名的 txt）→ 该文件显示“文件已损坏或无法读取”，同批其他文件照常完成。Task 3 与 Task 6 加测试。
3. **加密 PDF** → 显示“PDF 已加密，无法转换”，而不是英文堆栈。Task 3 加测试。
4. **同一批里两个同名源文件**（`a/报告.docx`、`b/报告.docx` 输出到同一目录）→ 输出 `报告.pdf` 和 `报告 (1).pdf`，不互相覆盖。Task 6 加测试。
5. **混合批次**（PDF + 图片一起选）→ 只显示两者都能到达的目标格式；空列表时界面提示“这些文件没有共同可转换的格式”。Task 2 加测试。

---

## 文件结构

```
requirements.txt          # 运行依赖
requirements-dev.txt      # -r requirements.txt + pytest + pyinstaller
pytest.ini                # testpaths = tests
app/__init__.py
app/main.py               # 入口 + --selftest
app/api.py                # Api 类（JS 桥）
app/logging_setup.py      # 日志文件位置与初始化
app/core/__init__.py      # 导入 converters 以完成注册
app/core/errors.py        # ConversionError
app/core/formats.py       # detect_format, OUTPUT_EXT, LABELS
app/core/naming.py        # unique_path
app/core/options.py       # Options dataclass
app/core/registry.py      # register, find_route, available_targets
app/core/pipeline.py      # convert_file, merge_images_to_pdf
app/core/converters/__init__.py
app/core/converters/pdf_image.py
app/core/converters/pdf_word.py
app/core/converters/pdf_excel.py
app/core/converters/office.py
app/web/index.html, style.css, app.js
build/file_converter.spec # PyInstaller
.github/workflows/build-windows.yml
.github/workflows/test.yml
tests/conftest.py         # 样例文件 fixture
tests/test_*.py
```

---

### Task 1: 项目骨架 + 格式 / 错误 / 命名 / 选项

**Files:**
- Create: `requirements.txt`, `requirements-dev.txt`, `pytest.ini`, `.gitignore`, `app/__init__.py`, `app/core/__init__.py`（暂为空）, `app/core/errors.py`, `app/core/formats.py`, `app/core/naming.py`, `app/core/options.py`
- Test: `tests/test_formats.py`, `tests/test_naming.py`

**Interfaces:**
- Produces:
  - `class ConversionError(Exception)`，`str(e)` 即中文提示。
  - `detect_format(path: Path) -> str | None`
  - `OUTPUT_EXT: dict[str, str]`（见 Global Constraints）
  - `LABELS: dict[str, str] = {"pdf": "PDF", "word": "Word", "excel": "Excel", "image": "PNG 图片"}`
  - `unique_path(directory: Path, filename: str) -> Path`：返回不存在的路径，必要时插入 ` (n)`。
  - `@dataclass class Options: dpi: int = 200; merge_images: bool = False`，`Options.from_dict(d: dict) -> Options`（忽略未知键，dpi 不在 {150,200,300} 时回落 200）。

- [ ] **Step 1: 写 requirements**

`requirements.txt`: `pywebview>=5.0`, `PyMuPDF`, `pdf2docx`, `pdfplumber`, `openpyxl`, `python-docx`。`requirements-dev.txt`: `-r requirements.txt`, `pytest`, `pyinstaller`。`.gitignore`: `__pycache__/`, `.pytest_cache/`, `build/dist/`, `build/work/`, `*.egg-info`。运行 `pip install -r requirements-dev.txt`，确认成功。

- [ ] **Step 2: 写失败测试**

```python
# tests/test_formats.py
def test_detect_format_case_insensitive():
    assert detect_format(Path("a/报告.DOCX")) == "word"
    assert detect_format(Path("x.Xls")) == "excel"
    assert detect_format(Path("p.JPG")) == "image"
    assert detect_format(Path("d.pdf")) == "pdf"
    assert detect_format(Path("n.txt")) is None

# tests/test_naming.py
def test_unique_path_free(tmp_path):
    assert unique_path(tmp_path, "报告.pdf") == tmp_path / "报告.pdf"
def test_unique_path_collisions(tmp_path):
    (tmp_path / "报告.pdf").touch(); (tmp_path / "报告 (1).pdf").touch()
    assert unique_path(tmp_path, "报告.pdf") == tmp_path / "报告 (2).pdf"
def test_options_from_dict():
    assert Options.from_dict({"dpi": 300, "merge_images": True, "x": 1}) == Options(300, True)
    assert Options.from_dict({"dpi": 999}).dpi == 200
```

- [ ] **Step 3: 运行确认失败** — `python -m pytest tests/test_formats.py tests/test_naming.py -v`，Expected: ImportError/FAIL。
- [ ] **Step 4: 实现** 上述 Produces 中的五个模块。
- [ ] **Step 5: 运行确认通过** — 同上命令，Expected: 全部 PASS。
- [ ] **Step 6: Commit** — `git commit -m "feat: 项目骨架与格式/命名/选项基础模块"`

---

### Task 2: 转换器注册表与路由

**Files:**
- Create: `app/core/registry.py`
- Test: `tests/test_registry.py`

**Interfaces:**
- Consumes: `detect_format`, `Options`（Task 1）
- Produces:
  - `Converter = Callable[[Path, Path, Options], list[Path]]` —— `(src, out_dir, opts) -> 输出文件列表（按顺序）`，输出写在 `out_dir`（临时目录），文件名由转换器自定，最终命名由 pipeline 负责。
  - `register(src: str, dst: str) -> decorator`，登记到模块级 `_EDGES: dict[tuple[str,str], Converter]`。
  - `find_route(src: str, dst: str) -> list[tuple[str, str, Converter]] | None`：BFS 最短路径；`src == dst` 或不可达返回 `None`。
  - `DISABLED: set[tuple[str,str]] = {("image","word"),("image","excel"),("word","excel"),("excel","word")}`
  - `available_targets(paths: list[Path]) -> list[str]`：每个文件可达且不在 DISABLED 的目标的**交集**，按 `["pdf","word","image","excel"]` 顺序；任一文件格式未知则该文件不参与（忽略），全部未知返回 `[]`。

- [ ] **Step 1: 写失败测试**（测试里用 fixture 临时替换 `_EDGES` 为假边：word→pdf、excel→pdf、pdf→image、image→pdf、pdf→word、pdf→excel，测试后恢复）

```python
def test_direct_route(fake_edges): assert [e[:2] for e in find_route("word","pdf")] == [("word","pdf")]
def test_two_hop_route(fake_edges): assert [e[:2] for e in find_route("excel","image")] == [("excel","pdf"),("pdf","image")]
def test_same_format_none(fake_edges): assert find_route("pdf","pdf") is None
def test_targets_word(fake_edges): assert available_targets([Path("a.docx")]) == ["pdf","image"]
def test_targets_pdf(fake_edges): assert available_targets([Path("a.pdf")]) == ["word","image","excel"]
def test_targets_image(fake_edges): assert available_targets([Path("a.png")]) == ["pdf"]
def test_targets_mixed_intersection(fake_edges):
    assert available_targets([Path("a.pdf"), Path("b.png")]) == []          # Review Focus 5
    assert available_targets([Path("a.docx"), Path("b.xlsx")]) == ["pdf","image"]
```

- [ ] **Step 2: 运行确认失败** — `python -m pytest tests/test_registry.py -v`
- [ ] **Step 3: 实现** `registry.py`。
- [ ] **Step 4: 运行确认通过**
- [ ] **Step 5: Commit** — `feat: 转换器注册表与 BFS 路由`

---

### Task 3: PDF ↔ 图片转换器 + 测试样例 fixture

**Files:**
- Create: `app/core/converters/__init__.py`, `app/core/converters/pdf_image.py`, `tests/conftest.py`
- Modify: `app/core/__init__.py`（`from .converters import pdf_image`，后续 Task 依次追加）
- Test: `tests/test_pdf_image.py`

**Interfaces:**
- Consumes: `register`, `Options`, `ConversionError`
- Produces:
  - `pdf_to_image(src, out_dir, opts) -> list[Path]`（`@register("pdf","image")`），每页一张 PNG，按页序返回，渲染倍率 `opts.dpi / 72`。
  - `image_to_pdf(src, out_dir, opts) -> list[Path]`（`@register("image","pdf")`），单图一页。
  - `images_to_single_pdf(srcs: list[Path], out_path: Path) -> Path`：多图合并（供 pipeline 用）。
  - `open_pdf(path: Path) -> fitz.Document`：统一打开 PDF；打开失败抛 `ConversionError("文件已损坏或无法读取")`，`doc.needs_pass` 时抛 `ConversionError("PDF 已加密，无法转换")`。后续 pdf_word / pdf_excel 也用它做前置检查。
  - conftest fixtures（文件名均为 `中文 样例.xxx`，放在 `tmp_path`）：`sample_pdf`（3 页，每页一行文字“第N页”）、`sample_table_pdf`（1 页含 3×2 表格，用 PyMuPDF 画线+写字，内容 `[["姓名","分数"],["张三","90"],["李四","85"]]`）、`sample_png`（100×50 红色）、`sample_docx`（python-docx，一段“你好世界”）、`sample_xlsx`（openpyxl，A1=“名称” B1=“数量”）、`encrypted_pdf`（PyMuPDF `save(..., encryption=fitz.PDF_ENCRYPT_AES_256, user_pw="1")`）、`corrupt_pdf`（写入 `b"not a pdf"`）。

- [ ] **Step 1: 写 conftest 与失败测试**

```python
def test_pdf_to_image_pages(sample_pdf, tmp_path):
    out = pdf_to_image(sample_pdf, tmp_path / "o", Options(dpi=150))
    assert len(out) == 3 and all(p.suffix == ".png" for p in out)
    assert fitz.open(out[0]).load_page(0).rect.width == pytest.approx(595 * 150 / 72, rel=0.02)
def test_image_to_pdf(sample_png, tmp_path):
    (pdf,) = image_to_pdf(sample_png, tmp_path / "o", Options())
    assert fitz.open(pdf).page_count == 1
def test_images_to_single_pdf(sample_png, tmp_path):
    assert fitz.open(images_to_single_pdf([sample_png, sample_png], tmp_path / "m.pdf")).page_count == 2
def test_encrypted_pdf(encrypted_pdf, tmp_path):
    with pytest.raises(ConversionError, match="PDF 已加密"): pdf_to_image(encrypted_pdf, tmp_path, Options())
def test_corrupt_pdf(corrupt_pdf, tmp_path):
    with pytest.raises(ConversionError, match="已损坏"): pdf_to_image(corrupt_pdf, tmp_path, Options())
```

（`sample_pdf` 页面为 A4，宽 595pt。converter 需自行 `out_dir.mkdir(parents=True, exist_ok=True)`。）

- [ ] **Step 2: 运行确认失败** — `python -m pytest tests/test_pdf_image.py -v`
- [ ] **Step 3: 实现** `pdf_image.py`（PyMuPDF：`page.get_pixmap(matrix=fitz.Matrix(z, z))`；图转 PDF 用 `fitz.open(img).convert_to_pdf()`）。
- [ ] **Step 4: 运行确认通过**
- [ ] **Step 5: Commit** — `feat: PDF 与图片互转`

---

### Task 4: PDF → Word、PDF → Excel

**Files:**
- Create: `app/core/converters/pdf_word.py`, `app/core/converters/pdf_excel.py`
- Modify: `app/core/__init__.py`（导入两者）
- Test: `tests/test_pdf_word.py`, `tests/test_pdf_excel.py`

**Interfaces:**
- Consumes: `register`, `Options`, `ConversionError`, `open_pdf`（Task 3，用于前置检查加密/损坏），fixtures
- Produces:
  - `pdf_to_word(src, out_dir, opts) -> list[Path]`（`@register("pdf","word")`），输出一个 `.docx`。
  - `pdf_to_excel(src, out_dir, opts) -> list[Path]`（`@register("pdf","excel")`），输出一个 `.xlsx`：每个含表格的页一个工作表，名为 `第N页`，同页多表之间空一行；**整份 PDF 没有任何表格时**抛 `ConversionError("PDF 中未找到表格")`。

- [ ] **Step 1: 写失败测试**

```python
def test_pdf_to_word(sample_pdf, tmp_path):
    (docx,) = pdf_to_word(sample_pdf, tmp_path / "o", Options())
    text = "\n".join(p.text for p in docx_lib.Document(docx).paragraphs)
    assert "第1页" in text and "第3页" in text
def test_pdf_to_word_encrypted(encrypted_pdf, tmp_path):
    with pytest.raises(ConversionError, match="PDF 已加密"): pdf_to_word(encrypted_pdf, tmp_path, Options())

def test_pdf_to_excel(sample_table_pdf, tmp_path):
    (xlsx,) = pdf_to_excel(sample_table_pdf, tmp_path / "o", Options())
    ws = openpyxl.load_workbook(xlsx)["第1页"]
    assert [[c.value for c in r] for r in ws.iter_rows(max_row=3)] == [["姓名","分数"],["张三","90"],["李四","85"]]
def test_pdf_to_excel_no_tables(sample_pdf, tmp_path):
    with pytest.raises(ConversionError, match="未找到表格"): pdf_to_excel(sample_pdf, tmp_path, Options())
```

（`sample_pdf` 的中文需用 PyMuPDF 内置中文字体 `fontname="china-s"` 写入，否则文字提取不到。conftest 里统一这样写。）

- [ ] **Step 2: 运行确认失败**
- [ ] **Step 3: 实现**（pdf2docx：`Converter(str(src)).convert(str(dst)); close()`；pdfplumber：`page.extract_tables()`）
- [ ] **Step 4: 运行确认通过** — `python -m pytest tests/test_pdf_word.py tests/test_pdf_excel.py -v`
- [ ] **Step 5: Commit** — `feat: PDF 转 Word 与 Excel`

---

### Task 5: LibreOffice（Word/Excel → PDF）

**Files:**
- Create: `app/core/converters/office.py`
- Modify: `app/core/__init__.py`
- Test: `tests/test_office.py`

**Interfaces:**
- Consumes: `register`, `Options`, `ConversionError`
- Produces:
  - `app_dir() -> Path`：冻结时 `Path(sys.executable).parent`，否则仓库根目录。
  - `find_soffice() -> Path | None`：依次检查 ① 环境变量 `FC_SOFFICE`；② `app_dir()/libreoffice/program/soffice.exe`；③ `shutil.which("soffice")`；④ `C:/Program Files/LibreOffice/program/soffice.exe`、`C:/Program Files (x86)/LibreOffice/program/soffice.exe`。返回第一个存在的。
  - `office_to_pdf(src, out_dir, opts) -> list[Path]`，同时 `@register("word","pdf")` 和 `@register("excel","pdf")`。

实现要点：
- 找不到 → `ConversionError("未找到 LibreOffice 组件，请重新解压完整的软件包")`。
- 全局 `threading.Lock` 串行；`subprocess.run([soffice, "--headless", "--norestore", f"-env:UserInstallation={profile.as_uri()}", "--convert-to", "pdf", "--outdir", str(out_dir), str(src)], timeout=120, capture_output=True)`，`profile` 为 `tempfile.mkdtemp()`，结束后删除；Windows 下传 `creationflags=subprocess.CREATE_NO_WINDOW`。
- 超时 → `ConversionError("转换超时（超过 120 秒）")`；返回码非 0 或输出 `out_dir/<src.stem>.pdf` 不存在 → `ConversionError("文件已损坏或无法读取")`。

- [ ] **Step 1: 写失败测试**（`needs_soffice = pytest.mark.skipif(find_soffice() is None, reason="无 LibreOffice")`）

```python
@needs_soffice
def test_docx_to_pdf(sample_docx, tmp_path):
    (pdf,) = office_to_pdf(sample_docx, tmp_path / "o", Options())
    assert "你好世界" in fitz.open(pdf).load_page(0).get_text()
@needs_soffice
def test_xlsx_to_pdf(sample_xlsx, tmp_path):
    (pdf,) = office_to_pdf(sample_xlsx, tmp_path / "o", Options())
    assert "名称" in fitz.open(pdf).load_page(0).get_text()
def test_missing_soffice(monkeypatch, sample_docx, tmp_path):
    monkeypatch.setattr(office, "find_soffice", lambda: None)
    with pytest.raises(ConversionError, match="未找到 LibreOffice"): office_to_pdf(sample_docx, tmp_path, Options())
def test_env_override(monkeypatch, tmp_path):
    fake = tmp_path / "soffice"; fake.touch(); monkeypatch.setenv("FC_SOFFICE", str(fake))
    assert find_soffice() == fake
```

- [ ] **Step 2: 运行确认失败** — `python -m pytest tests/test_office.py -v`
- [ ] **Step 3: 实现**
- [ ] **Step 4: 运行确认通过**（本地 Linux 有 `/usr/bin/soffice`，两个 needs_soffice 测试应实际运行并 PASS）
- [ ] **Step 5: Commit** — `feat: LibreOffice 转换 Word/Excel 为 PDF`

---

### Task 6: Pipeline（多步执行 + 最终命名）

**Files:**
- Create: `app/core/pipeline.py`
- Test: `tests/test_pipeline.py`

**Interfaces:**
- Consumes: `find_route`, `detect_format`, `OUTPUT_EXT`, `unique_path`, `images_to_single_pdf`, `ConversionError`, `Options`
- Produces:
  - `convert_file(src: Path, target: str, out_dir: Path | None, opts: Options) -> list[Path]`：`out_dir is None` 时用 `src.parent`；在 `tempfile.TemporaryDirectory()` 里按路由逐步执行（上一步每个输出都作为下一步输入，结果展平）；最终文件移动到 `out_dir`：只有一个输出 → `unique_path(out_dir, f"{src.stem}{ext}")`；多个 → 第 i 个（从 1 起）为 `unique_path(out_dir, f"{src.stem}_第{i}页{ext}")`。返回最终路径。格式未知 → `ConversionError("不支持的文件格式")`；无路由或在 `DISABLED` → `ConversionError("不支持转换为该格式")`。
  - `merge_images_to_pdf(srcs: list[Path], out_dir: Path | None) -> Path`：输出 `unique_path(out_dir or srcs[0].parent, f"{srcs[0].stem}_合并.pdf")`。

- [ ] **Step 1: 写失败测试**

```python
def test_pdf_to_images_named(sample_pdf, tmp_path):
    out = convert_file(sample_pdf, "image", tmp_path, Options())
    assert [p.name for p in out] == ["中文 样例_第1页.png", "中文 样例_第2页.png", "中文 样例_第3页.png"]
def test_default_out_dir_is_source_dir(sample_png):
    (pdf,) = convert_file(sample_png, "pdf", None, Options()); assert pdf.parent == sample_png.parent
def test_same_stem_no_overwrite(tmp_path, make_png):          # Review Focus 4
    a, b = make_png(tmp_path / "a" / "报告.png"), make_png(tmp_path / "b" / "报告.png")
    out = tmp_path / "out"
    assert convert_file(a, "pdf", out, Options())[0].name == "报告.pdf"
    assert convert_file(b, "pdf", out, Options())[0].name == "报告 (1).pdf"
def test_disabled_target(sample_png, tmp_path):
    with pytest.raises(ConversionError, match="不支持转换为该格式"): convert_file(sample_png, "word", tmp_path, Options())
def test_unknown_format(tmp_path):
    f = tmp_path / "a.txt"; f.write_text("x")
    with pytest.raises(ConversionError, match="不支持的文件格式"): convert_file(f, "pdf", tmp_path, Options())
def test_corrupt_raises_cleanly(corrupt_pdf, tmp_path):          # Review Focus 2
    with pytest.raises(ConversionError): convert_file(corrupt_pdf, "image", tmp_path / "o", Options())
def test_merge_images(sample_png, tmp_path):
    p = merge_images_to_pdf([sample_png, sample_png], tmp_path)
    assert p.name == "中文 样例_合并.pdf" and fitz.open(p).page_count == 2
@needs_soffice
def test_two_hop_docx_to_png(sample_docx, tmp_path):
    out = convert_file(sample_docx, "image", tmp_path / "o", Options())
    assert [p.name for p in out] == ["中文 样例.png"]
```

（在 conftest 增加 `make_png(path) -> Path` 工厂 fixture，自动建父目录；`needs_soffice` 挪到 conftest 共用。注意最后一个用例：单页 docx 只产出一张图 → 按“单输出”规则命名，不带“第1页”。）

- [ ] **Step 2: 运行确认失败**
- [ ] **Step 3: 实现** `pipeline.py`
- [ ] **Step 4: 运行全部测试** — `python -m pytest -v`，Expected: 全 PASS
- [ ] **Step 5: Commit** — `feat: 多步转换流水线与输出命名`

---

### Task 7: Api 桥接层 + 日志 + 入口 / 自检

**Files:**
- Create: `app/api.py`, `app/logging_setup.py`, `app/main.py`
- Test: `tests/test_api.py`

**Interfaces:**
- Consumes: `available_targets`, `convert_file`, `merge_images_to_pdf`, `detect_format`, `LABELS`, `Options`, `ConversionError`
- Produces:
  - `setup_logging() -> Path`：建日志目录（见 Global Constraints），配置 root logger 写文件，返回日志路径。
  - `class Api`：`__init__(self)`；`attach(self, window)`（存 window，供推送）。以下方法供 JS 调用（pywebview 会把公开方法暴露为 `window.pywebview.api.<name>`，**不要把 window 存为公开属性**，用 `self._window`）：
    - `describe(paths: list[str]) -> list[dict]` → 每项 `{"path", "name", "format", "label"}`，未知格式 `format=None`。
    - `get_targets(paths: list[str]) -> list[dict]` → `[{"key": "pdf", "label": "PDF"}, ...]`。
    - `pick_files() -> list[str]` / `pick_folder() -> str | None`：调用 `self._window.create_file_dialog(webview.OPEN_DIALOG, allow_multiple=True, file_types=("支持的文件 (*.pdf;*.docx;*.doc;*.xlsx;*.xls;*.png;*.jpg;*.jpeg)",))` / `FOLDER_DIALOG`。
    - `start(paths: list[str], target: str, out_dir: str | None, options: dict) -> None`：启动后台线程跑 `run_batch` 并立即返回。
    - `open_folder(path: str) -> None`：Windows 用 `os.startfile`，其他平台 `xdg-open`。
    - `run_batch(paths, target, out_dir, options) -> None`（同步，测试直接调）：若 `target == "pdf"`、`options.merge_images` 且所有文件都是 image → 一次 `merge_images_to_pdf`，所有行一起推 done；否则逐个 `convert_file`。每个文件开始推 `{"type":"status","index":i,"state":"running"}`，结束推 `state":"done","outputs":[str...]` 或 `"state":"error","message":<中文>`；`ConversionError` 用其消息，其他异常 `logging.exception` 后消息为 `f"转换失败：{type(e).__name__}"`。全部结束推 `{"type":"finished","ok":n,"failed":m,"out_dir":<第一个成功输出的目录或 None>}`。推送方式：`self._window.evaluate_js(f"window.onBackendEvent({json.dumps(evt, ensure_ascii=False)})")`。
  - `app/main.py`：`main(argv=None) -> int`。`--selftest`：在临时目录用 python-docx 生成 `自检.docx`，`convert_file(..., "pdf", ...)`，成功则把 `OK` 写入 `app_dir()/selftest.log` 并返回 0，否则写入错误并返回 1。正常启动：`setup_logging()`；`api = Api()`；`window = webview.create_window("文件转换器", url=<app/web/index.html 的路径，冻结时在 sys._MEIPASS 下>, js_api=api, width=900, height=680, min_size=(720, 520))`；`api.attach(window)`；用 pywebview 5 的 DOM 事件处理拖放：在 `window.events.loaded` 回调中 `window.dom.document.events.drop += DOMEventHandler(on_drop, prevent_default=True, stop_propagation=True)`，`dragover` 同样 `prevent_default=True`；`on_drop` 取 `e["dataTransfer"]["files"][i]["pywebviewFullPath"]`，调用 `window.evaluate_js(f"window.addFiles({json.dumps(paths, ensure_ascii=False)})")`。最后 `webview.start()`。`if __name__ == "__main__": sys.exit(main())`。

- [ ] **Step 1: 写失败测试**（`FakeWindow` 收集 `evaluate_js` 的字符串，解析出 JSON 事件）

```python
def test_get_targets(sample_pdf):
    assert [t["key"] for t in Api().get_targets([str(sample_pdf)])] == ["word","image","excel"]
def test_batch_continues_after_failure(sample_png, corrupt_pdf, tmp_path):   # Review Focus 2
    api, w = make_api()
    api.run_batch([str(corrupt_pdf), str(sample_png)], "pdf", str(tmp_path / "o"), {})
    ev = w.events()
    assert ev[1] == {"type":"status","index":0,"state":"error","message": ANY_STR}
    assert ev[-2]["state"] == "done" and ev[-1]["ok"] == 1 and ev[-1]["failed"] == 1
def test_unexpected_exception_message(monkeypatch, sample_png, tmp_path):
    monkeypatch.setattr(api_mod, "convert_file", lambda *a: (_ for _ in ()).throw(ValueError("x")))
    api, w = make_api(); api.run_batch([str(sample_png)], "pdf", str(tmp_path), {})
    assert w.events()[1]["message"] == "转换失败：ValueError"
def test_merge_images_batch(sample_png, tmp_path):
    api, w = make_api(); api.run_batch([str(sample_png)]*2, "pdf", str(tmp_path), {"merge_images": True})
    assert w.events()[-1]["ok"] == 2 and len(list(tmp_path.glob("*.pdf"))) == 1
def test_selftest_ok():   # 需 soffice
    assert main(["--selftest"]) == 0
```

（`ANY_STR` 为 `class _Any: __eq__ = lambda s, o: isinstance(o, str)` 的实例；`test_selftest_ok` 加 `needs_soffice`。为避免往仓库根写文件，`main` 写 selftest.log 前读取环境变量 `FC_SELFTEST_LOG` 覆盖路径，测试里用 monkeypatch 指到 tmp_path。）

- [ ] **Step 2: 运行确认失败** — `python -m pytest tests/test_api.py -v`
- [ ] **Step 3: 实现** `logging_setup.py`、`api.py`、`main.py`
- [ ] **Step 4: 运行全部测试通过**
- [ ] **Step 5: Commit** — `feat: JS 桥接层、日志与程序入口`

---

### Task 8: 界面（HTML/CSS/JS）

**Files:**
- Create: `app/web/index.html`, `app/web/style.css`, `app/web/app.js`

**Interfaces:**
- Consumes: `window.pywebview.api.{describe,get_targets,pick_files,pick_folder,start,open_folder}`（Task 7）；后端调用的全局函数 `window.addFiles(paths: string[])`、`window.onBackendEvent(evt)`。

布局与文案（规格第 5 节）：
1. 拖放区：“把文件拖到这里，或点击添加”，点击 → `pick_files()` → `addFiles`。
2. 文件列表：每行 文件名 / 格式标签 / 状态（排队中、转换中…、✅ 完成、❌ <message>）/ 移除按钮；右上角「清空」。同一路径重复添加时忽略。未知格式行显示“❌ 不支持的文件格式”，不参与 `get_targets` 与转换。
3. 设置：目标格式按钮组（来自 `get_targets`，空时显示“这些文件没有共同可转换的格式”）；输出位置：单选“和原文件相同”/“指定文件夹…”（点后 `pick_folder()`，显示所选路径）；仅当目标为 image 时显示清晰度（标准 150 / 高清 200（默认）/ 超清 300）；仅当目标为 pdf 且所有文件都是 image 时显示“合并为一个 PDF”复选框。
4. 「开始转换」：无有效文件或未选目标时禁用；转换中禁用所有设置、添加、移除；`finished` 后显示“完成 n 个，失败 m 个”，`out_dir` 非空时显示「打开输出文件夹」。

风格：浅色，系统字体 `"Microsoft YaHei UI", "Segoe UI", sans-serif`，单一强调色，卡片分区；页面在 720×520 最小尺寸下不出现横向滚动。JS 需在 `pywebviewready` 事件后再调用 api。

- [ ] **Step 1: 实现三个文件**
- [ ] **Step 2: 本地冒烟** —— 用浏览器打开 `app/web/index.html`，注入假的 `window.pywebview.api`（在控制台或用 Playwright 脚本 `page.add_init_script`），调用 `addFiles(["C:/a/报告.pdf","C:/a/图.png"])`，确认：列表两行；目标区显示无共同格式提示；移除 PDF 后出现「PDF」按钮和“合并为一个 PDF”；模拟 `onBackendEvent` 的 running/done/error/finished 后状态与汇总正确。用 Playwright 截图 `docs/screenshots/ui.png` 供用户查看。
- [ ] **Step 3: Commit** — `feat: 桌面界面`

---

### Task 9: Windows 打包与 CI

**Files:**
- Create: `build/file_converter.spec`, `.github/workflows/build-windows.yml`, `.github/workflows/test.yml`, `README.md`

**Interfaces:**
- Consumes: `app/main.py` 的 `main()` 与 `--selftest`、`find_soffice()` 的查找顺序 ②（`<exe 目录>/libreoffice/program/soffice.exe`）。

要点：
- **spec**：入口 `app/main.py`；`datas=[("../app/web", "app/web")]`；`console=False`；`name="文件转换器"`；onedir（`COLLECT`）；`collect_all("fitz")`/`collect_all("pdf2docx")` 视需要加 hiddenimports。若中文 exe 名在 CI 里出问题，退回 `FileConverter.exe` 并在 README 说明。
- **test.yml**（push 时）：ubuntu-latest，`apt-get install -y libreoffice-writer libreoffice-calc`，`pip install -r requirements-dev.txt`，`python -m pytest -v`。
- **build-windows.yml**（push 到本分支及手动触发）：windows-latest，Python 3.12：
  1. `pip install -r requirements-dev.txt`；`python -m pytest -v`（此时还没有 LibreOffice，`needs_soffice` 测试自动跳过；LibreOffice 路径由第 5 步自检覆盖）。
  2. `pyinstaller build/file_converter.spec --distpath build/dist --workpath build/work`。
  3. 下载 LibreOffice MSI：版本用环境变量 `LO_VERSION` 固定（实施时到 `https://download.documentfoundation.org/libreoffice/stable/` 取当前 stable 版本号），URL `https://download.documentfoundation.org/libreoffice/stable/${LO_VERSION}/win/x86_64/LibreOffice_${LO_VERSION}_Win_x86-64.msi`；用 `actions/cache` 以版本号为 key 缓存 MSI。
  4. `msiexec /a LibreOffice.msi /qn TARGETDIR=$PWD\lo_extract`（`Start-Process -Wait`）；用 `Get-ChildItem -Recurse -Filter soffice.exe` 找到 `program` 目录，把它的**父目录**整体移动为 `build/dist/文件转换器/libreoffice`，断言 `libreoffice/program/soffice.exe` 存在。
  5. 自检：`$p = Start-Process build/dist/文件转换器/文件转换器.exe -ArgumentList "--selftest" -Wait -PassThru`；`$p.ExitCode -eq 0` 且 `selftest.log` 内容为 `OK`，否则打印 log 并失败。
  6. `Compress-Archive` 为 `文件转换器-windows.zip`，`actions/upload-artifact` 上传（retention 30 天）。
- **README.md**（中文）：功能、下载方式（Actions → 最新一次 build-windows → Artifacts）、使用方法、开发命令（`pip install -r requirements-dev.txt`、`python -m pytest`、`python -m app.main`）、日志位置。

- [ ] **Step 1: 写 spec、两个 workflow、README**
- [ ] **Step 2: 本地验证** —— `python -m pytest -v` 全过；`python -c "import yaml,sys; [yaml.safe_load(open(f)) for f in sys.argv[1:]]" .github/workflows/*.yml` 无报错（无 PyYAML 时 `pip install pyyaml`）。
- [ ] **Step 3: Commit 并 push**，到 GitHub 查看两个 workflow 运行结果；失败则读日志修复后再推，直到 build-windows 产出 zip 且自检通过。
- [ ] **Step 4: Commit** — `ci: Windows 打包（内置 LibreOffice）与测试流水线`
