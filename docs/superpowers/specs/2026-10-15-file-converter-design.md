# 文件格式转换器 设计文档

日期：2026-10-15
状态：待用户审阅

## 1. 目标

一个给自己用的 Windows 桌面软件，在 Word、PDF、PNG、Excel 之间互相转换。
离线运行，开箱即用（不需要另外安装 LibreOffice）。

**成功标准**

- 解压后双击 `文件转换器.exe` 即可使用，无需安装 Python 或 LibreOffice。
- 拖入多个文件 → 选目标格式 → 点「开始转换」→ 输出到指定文件夹。
- 第一版支持的转换（见第 4 节）全部可用，单个文件失败不影响其他文件。

**不做（第一版）**

- OCR（图片 → Word/Excel）、Word ↔ Excel —— 放到第二版。
- 右键菜单、命令行、自动更新、多语言。
- macOS / Linux 打包（核心代码跨平台，但只发布 Windows 版）。

## 2. 技术选型

| 部分 | 选择 | 理由 |
|---|---|---|
| 语言 | Python 3.12 | 转换库最全 |
| 窗口 | pywebview（Windows 下使用 Edge WebView2） | 系统自带 WebView2，体积小；JS 可直接调用 Python |
| 界面 | 原生 HTML/CSS/JS，无框架、无构建步骤 | 单页工具，够用且好维护 |
| Word/Excel → PDF | LibreOffice（随软件打包） | 免费、效果好、离线 |
| PDF ↔ 图片 | PyMuPDF | 快、质量高 |
| PDF → Word | pdf2docx | 保留版式最好的开源方案 |
| PDF → Excel | pdfplumber + openpyxl | 表格提取成熟 |
| 打包 | PyInstaller（onedir）+ GitHub Actions（windows-latest） | 开发环境是 Linux，由 CI 在 Windows 上打包 |
| 测试 | pytest | 测核心转换逻辑 |

## 3. 架构

```
文件转换器/
├─ app/
│  ├─ main.py            # 入口：创建 pywebview 窗口，挂载 Api
│  ├─ api.py             # 桥接层：JS 调用的方法，后台线程执行任务，推送进度
│  ├─ core/
│  │  ├─ formats.py      # 格式定义：扩展名 → 格式（docx/doc→word, xlsx/xls→excel, png/jpg/jpeg→image, pdf）
│  │  ├─ registry.py     # 转换器注册表 + 路由（BFS 求最短转换路径）
│  │  ├─ pipeline.py     # 按路径执行多步转换，管理临时目录，单文件出错不中断批次
│  │  ├─ errors.py       # ConversionError（带中文提示）
│  │  └─ converters/
│  │     ├─ office.py    # word→pdf, excel→pdf（LibreOffice）
│  │     ├─ pdf_image.py # pdf→image, image→pdf（PyMuPDF）
│  │     ├─ pdf_word.py  # pdf→word（pdf2docx）
│  │     └─ pdf_excel.py # pdf→excel（pdfplumber + openpyxl）
│  └─ web/
│     ├─ index.html
│     ├─ style.css
│     └─ app.js
├─ tests/                # pytest，样例文件在测试中现场生成
├─ build/                # PyInstaller spec、打包脚本
└─ .github/workflows/build-windows.yml
```

**分层原则**：`core/` 不依赖界面，可单独测试，以后加命令行或右键菜单直接复用。

### 3.1 转换器接口

每个转换器是一个函数，登记为图中的一条边：

```python
@register(src="pdf", dst="image")
def pdf_to_image(src: Path, out_dir: Path, opts: Options) -> list[Path]:
    ...
```

- 输入一个文件，输出**一个或多个**文件（PDF → PNG 每页一张）。
- 多步路径中，上一步输出多个文件时，下一步逐个处理（例：Word → PDF → PNG 正常；目前不存在“多文件再合并”的中间步骤）。

### 3.2 路由

注册表构成有向图，用 BFS 找最短路径。第一版的边：

| 边 | 实现 |
|---|---|
| word → pdf | LibreOffice |
| excel → pdf | LibreOffice |
| pdf → image | PyMuPDF，默认 200 DPI，每页一张 PNG |
| image → pdf | PyMuPDF，**批量模式下可选“合并为一个 PDF”** |
| pdf → word | pdf2docx |
| pdf → excel | pdfplumber，每个 PDF 页的表格写入一个工作表 |

由此自动得到：word → image、excel → image（经 PDF）；image → word、image → excel 也能走通（经 PDF），但图片 PDF 里没有文字，结果为空，**界面上对这两项不提供**（第二版接 OCR 后开放）。

界面根据所选文件的格式，只显示可用的目标格式。

### 3.3 LibreOffice 打包与调用

- CI 下载 LibreOffice Windows MSI，用 `msiexec /a`（管理安装）解包到 `libreoffice/` 目录，与 exe 放在一起。
- 运行时查找顺序：① 程序目录下的 `libreoffice/program/soffice.exe`；② 系统已安装的 LibreOffice（常见路径 / 注册表）。都找不到则报错“未找到 LibreOffice 组件”。
- 调用方式：`soffice --headless --convert-to pdf --outdir <临时目录> <文件>`，并使用独立的配置目录 `-env:UserInstallation=file:///<临时目录>`，避免和用户自己打开的 LibreOffice 冲突。
- LibreOffice 调用**串行执行**（加锁），设超时 120 秒/文件。

### 3.4 数据流

1. 用户拖入文件 / 点「添加文件」（pywebview 文件对话框）→ 前端拿到路径列表。
2. 前端调用 `api.get_targets(paths)` → 返回这批文件共同可用的目标格式。
3. 用户选目标格式、输出目录（默认：源文件所在目录）→ 调用 `api.start(paths, target, out_dir, options)`。
4. `api` 在后台线程逐个文件执行 `pipeline.run()`，每完成一个通过 `window.evaluate_js` 推送状态（排队/转换中/成功/失败+原因）。
5. 全部完成后显示汇总，提供「打开输出文件夹」按钮。

### 3.5 输出命名

- 单文件输出：`原名.目标扩展名`，如 `报告.pdf`。
- 多文件输出（PDF → PNG）：`原名_第1页.png`、`原名_第2页.png`……
- 重名时自动加序号：`报告 (1).pdf`，**绝不覆盖已有文件**。

## 4. 第一版转换矩阵

| 输入 ↓ / 输出 → | PDF | Word | PNG | Excel |
|---|---|---|---|---|
| Word (.docx/.doc) | ✅ | — | ✅ | ⏸ |
| Excel (.xlsx/.xls) | ✅ | ⏸ | ✅ | — |
| PDF | — | ✅ | ✅ | ✅ |
| 图片 (.png/.jpg) | ✅ | ⏸ OCR | — | ⏸ OCR |

## 5. 界面

单窗口，自上而下：

1. **拖放区**：“把文件拖到这里，或点击添加”。
2. **文件列表**：文件名、格式、状态（排队 / 转换中 / ✅ 成功 / ❌ 失败+原因），可移除单个、清空。
3. **设置栏**：目标格式（按钮组，只显示可用项）；输出文件夹（默认“和原文件相同”，可选择）；图片相关选项（PDF → PNG 的清晰度：标准 150 / 高清 200 / 超清 300 DPI；图片 → PDF 是否合并为一个文件）。
4. **操作**：「开始转换」、完成后「打开输出文件夹」。

转换进行中禁用设置和开始按钮。

## 6. 错误处理

- 所有可预期错误抛 `ConversionError(中文提示)`，显示在对应文件行上。
- 典型提示：不支持的格式；文件已加密/损坏；未找到 LibreOffice 组件；转换超时；PDF 中未找到表格（PDF → Excel）。
- 未预期异常：捕获后显示“转换失败：<异常简述>”，完整堆栈写入日志文件 `%LOCALAPPDATA%/文件转换器/logs/app.log`。
- 临时文件放在系统临时目录，每个文件处理完即清理。

## 7. 测试

- **单元测试（pytest，Linux 上 CI 和本地都跑）**：
  - 格式识别、路由（各组合的路径、不可达组合）、输出命名（重名加序号）。
  - 每个转换器：测试中用 python-docx / openpyxl / PyMuPDF 现场生成样例，转换后检查输出存在、页数/表格内容正确。
  - LibreOffice 相关测试在没有 soffice 的环境自动跳过。
- **api 层**：用假的 window 对象测试状态推送和“单个失败不影响其他”。
- **界面**：不做自动化测试，由用户在 Windows 上手动试用。
- **打包验证**：GitHub Actions 在 Windows 上打包后，运行一次无界面自检（`文件转换器.exe --selftest`：调用核心把生成的 docx 转 PDF），确认打包的 LibreOffice 可用。

## 8. 发布

- GitHub Actions 产出 `文件转换器-windows.zip`（约 500MB 解压后），在 Actions 页面下载。
- 第一版用 zip 绿色版（解压即用）；安装程序（Inno Setup）以后需要再加。

## 9. 第二版候选（不在本次范围）

- OCR：图片 → Word / Excel（RapidOCR）。
- Word ↔ Excel。
- 右键菜单集成。
- PDF 合并 / 拆分 / 压缩。
