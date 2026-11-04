# 公文排版 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 单独的 Windows 桌面软件「公文排版」：.docx 或粘贴文字 → 自动识别段落类型 → 预览修改 → 导出单位公文格式 .docx。

**Architecture:** `gongwen/core/` 是纯 Python 核心：reader 读入为 Block 列表，classify 标注类型与文种，build 按 skill 参数生成 .docx。`gongwen/api.py` 为 pywebview JS 桥，`gongwen/web/` 为无框架单页界面（左段落列表 + 右 A4 实时预览）。GitHub Actions 在 Windows 上 PyInstaller 打包并自检。

**Tech Stack:** Python 3.12，python-docx，pywebview ≥5，pytest，Playwright（界面冒烟），PyInstaller。

**Spec:** `docs/superpowers/specs/2026-11-04-gongwen-formatter-design.md`

## Global Constraints

- `gongwen/` 不得 import `app/`（两个软件互不依赖）；不依赖 LibreOffice。
- 块类型固定为：`title addressee h1 h2 h3 body attachment signer date table`；文种：`notice | brief`。
- 识别阈值：`SHORT = 30`（主送机关）、`TITLE_MAX = 40`（标题第二行）、`SIGNER_MAX = 20`（落款）、`H_MAX = 50`（超过且以“。”结尾的序号段落判为正文）。
- 格式参数严格按 spec 第 4 节（即 skill `gw_build.py`）：标题 方正小标宋简体 22pt；主送机关/一级 黑体 16pt；二级 楷体_GB2312 16pt；正文/三级/附件/落款/日期 仿宋_GB2312 16pt；表格 表头黑体、内容仿宋 14pt；页码 9pt。行距固定 26pt，段前 0，段后 8pt；首行缩进 `firstLineChars=200`；不加粗；四个字体槽同一字体。A4，上下 2.54cm，左右 3.17cm，页眉 1.5cm，页脚 1.75cm，docGrid type=lines linePitch=312。
- 用户可见文字一律中文；可预期错误抛 `GongwenError(中文提示)`。
- 日志：`%LOCALAPPDATA%/公文排版/logs/app.log`（非 Windows：`~/.local/share/公文排版/logs/app.log`）。
- 默认导出文件名：标题各行拼接，去掉 `\/:*?"<>|`，空则为 `公文`，扩展名 `.docx`。
- 产物：`公文排版-windows.zip`，内含 `公文排版/公文排版.exe` 与 `公文排版/公文排版.exe.config`（复制 `build/app.exe.config`）。

## Review Focus

1. **段落内手动换行**（Word 里 Shift+Enter 断开的两行标题，python-docx 读成含 `\n` 的一段）→ 拆成多段，标题仍识别为两行。Task 2 加测试。
2. **序号写法不规范**（`　　一、` 段首全角空格、`一 、`、`(一)`、`（一)`、`1．`）→ 清理后照常识别为对应层级。Task 3 加测试。
3. **只有一行 / 全是正文 / 表格在最前面** → 不报错；表格不参与标题判断，第一个非表格段落为标题。Task 3 加测试。
4. **导出时目标文件正被 Word 打开**（PermissionError）→ “文件正在被其他程序使用，请先关闭它或换个文件名”，不是英文堆栈。Task 5 加测试。
5. **标题含文件名非法字符或为空**（`关于“A/B”的通知`）→ 默认文件名 `关于“AB”的通知.docx`；无标题 → `公文.docx`。Task 4 加测试。

---

## 文件结构

```
gongwen/__init__.py
gongwen/core/__init__.py
gongwen/core/errors.py      GongwenError
gongwen/core/model.py       Block, Document, TYPES, KINDS
gongwen/core/dates.py       normalize_date
gongwen/core/reader.py      read_docx, read_text
gongwen/core/classify.py    classify
gongwen/core/build.py       build_docx, default_filename
gongwen/logging_setup.py    setup_logging
gongwen/api.py              Api
gongwen/main.py             main, selftest
gongwen/web/index.html, style.css, app.js
tests/gongwen/__init__.py   （空，避免与 tests/ 同名模块冲突）
tests/gongwen/test_*.py
tools/gongwen_ui_smoke.py
build/gongwen.spec
.github/workflows/build-gongwen.yml
README.md（追加「公文排版」一节）
```

---

### Task 1: 数据结构、错误、日期规范化

**Files:**
- Create: `gongwen/__init__.py`, `gongwen/core/__init__.py`, `gongwen/core/errors.py`, `gongwen/core/model.py`, `gongwen/core/dates.py`
- Test: `tests/gongwen/__init__.py`, `tests/gongwen/test_model.py`, `tests/gongwen/test_dates.py`

**Interfaces:**
- Produces:
  - `class GongwenError(Exception)`
  - `TYPES = ("title","addressee","h1","h2","h3","body","attachment","signer","date","table")`，`KINDS = ("notice","brief")`
  - `@dataclass Block: t: str; text: str = ""; rows: list[list[str]] | None = None`；`to_dict() -> dict`（table 为 `{"t","rows"}`，其余 `{"t","text"}`）；`Block.from_dict(d) -> Block`（t 不在 TYPES → `GongwenError("段落类型无效")`）
  - `@dataclass Document: kind: str; blocks: list[Block]`；`to_dict()` → `{"kind", "blocks": [...]}`；`Document.from_dict(d)`（kind 不在 KINDS → GongwenError）
  - `normalize_date(s: str) -> str`

- [ ] **Step 1: 写失败测试**

```python
def test_roundtrip():
    d = Document("notice", [Block("title", "关于…"), Block("table", rows=[["a","b"]])])
    assert Document.from_dict(d.to_dict()) == d
    assert d.to_dict()["blocks"][1] == {"t": "table", "rows": [["a", "b"]]}
def test_invalid_type():
    with pytest.raises(GongwenError): Block.from_dict({"t": "xx", "text": ""})

@pytest.mark.parametrize("src,dst", [
    ("二〇二六年八月二十四日", "2026年8月24日"), ("二〇二六年十月一日", "2026年10月1日"),
    ("二零二六年十二月三十一日", "2026年12月31日"), ("2026年8月24日", "2026年8月24日"),
    ("二〇二六年十三月一日", "二〇二六年十三月一日"), ("八月", "八月")])
def test_normalize_date(src, dst): assert normalize_date(src) == dst
```

- [ ] **Step 2: 运行确认失败** — `python -m pytest tests/gongwen -q`
- [ ] **Step 3: 实现**（日期：正则 `^([〇零一二三四五六七八九]{4})年([一二三四五六七八九十]{1,3})月([一二三四五六七八九十]{1,3})日$`；月 1–12、日 1–31 校验失败原样返回）
- [ ] **Step 4: 运行确认通过**
- [ ] **Step 5: Commit** — `feat(公文排版): 数据结构与日期规范化`

---

### Task 2: 读入（.docx / 粘贴文字）

**Files:**
- Create: `gongwen/core/reader.py`
- Test: `tests/gongwen/test_reader.py`

**Interfaces:**
- Consumes: `Block`, `GongwenError`
- Produces:
  - `read_docx(path: Path) -> list[Block]`：段落 → `Block("body", text)`，表格 → `Block("table", rows=...)`，按文档顺序（遍历 `doc.element.body` 子元素 `w:p` / `w:tbl`）。
  - `read_text(text: str) -> list[Block]`：全部为 `body`。
  - 两者共用 `_clean_lines(text) -> list[str]`：按 `\r\n|\r|\n` 拆分（段落内 `<w:br>` 在 python-docx 中即 `\n`），去首尾半角/全角空格与制表符（`strip(" \t\u3000\xa0")`），丢弃空行。
  - 后缀 `.doc` → `GongwenError("暂不支持老版 .doc 文件，请先用「文件转换器」转为 .docx，或复制文字后点「粘贴文字」")`；打不开 → `GongwenError("文件已损坏或无法读取")`；结果为空 → `GongwenError("没有读到任何文字")`。

- [ ] **Step 1: 写失败测试**（`tmp_path` 里用 python-docx 现场生成样例，文件名带中文和空格）

```python
def test_read_docx_order_and_table(tmp_path):   # 段落、表格、段落
    assert [b.t for b in read_docx(p)] == ["body", "table", "body"]
    assert read_docx(p)[1].rows == [["监区", "人数"], ["一监区", "12"]]
def test_soft_line_break_splits(tmp_path):        # Review Focus 1：run.add_break() 断开的两行
    assert [b.text for b in read_docx(p)][:2] == ["关于组织学习临释罪犯再犯风险评估", "相关内容的通知"]
def test_clean_and_drop_empty():
    assert [b.text for b in read_text("　　一、标题\r\n\r\n  正文。\t\n")] == ["一、标题", "正文。"]
def test_doc_rejected(tmp_path):   match="老版 .doc"
def test_corrupt(tmp_path):        match="已损坏"     # 写入 b"not a zip"，后缀 .docx
def test_empty(tmp_path):          match="没有读到任何文字"   # 空 Document 与 read_text("  \n ")
```

- [ ] **Step 2: 运行确认失败** — `python -m pytest tests/gongwen/test_reader.py -q`
- [ ] **Step 3: 实现**
- [ ] **Step 4: 运行确认通过**
- [ ] **Step 5: Commit** — `feat(公文排版): 读入 Word 与粘贴文字`

---

### Task 3: 自动识别

**Files:**
- Create: `gongwen/core/classify.py`
- Test: `tests/gongwen/test_classify.py`

**Interfaces:**
- Consumes: `Block`, `Document`
- Produces: `classify(blocks: list[Block]) -> Document`（返回新对象，输入块的 `t` 视为未标注；table 块保持 `table`）

规则即 spec 3.3，按顺序实现；补充决定：
- 序号匹配前先把段首的序号规范化判断：允许序号与“、”之间有空格（`一 、`），允许中英文括号混用（`(一)`、`（一)`）。只用于判断，不改文字。
- “附件”行本身不产出块；附件项 text 去掉序号（`1、` `1.` `1．` `（1）` `(1)`）。
- 日期块的 text 保持原样（规范化在 build 时做）。
- 落款只在识别出日期时判断。

- [ ] **Step 1: 写失败测试**

```python
NOTICE = """关于组织学习临释罪犯再犯风险评估
相关内容的通知
狱属各监区：
为进一步规范评估工作，具体通知如下：
一、认真组织学习，准确掌握量表填写要求
（一）系统初评为一般危险等级的
1、《临释罪犯再犯风险评估报告》；
一是要认真学。各监区要组织民警逐条学习。
附件：
1.《罪犯再犯风险评估量表（成年男犯）》及填写说明
2、《评估报告模板》
评估矫治中心
二〇二六年八月二十四日"""

def test_notice_end_to_end():
    d = classify(read_text(NOTICE))
    assert d.kind == "notice"
    assert [b.t for b in d.blocks] == ["title","title","addressee","body","h1","h2","h3","body",
                                       "attachment","attachment","signer","date"]
    assert d.blocks[8].text == "《罪犯再犯风险评估量表（成年男犯）》及填写说明"

BRIEF = "心理为钥，精准疏导解心结\n近日，某监区开展心理疏导活动。\n一、全员覆盖筑根基，多维教育润心田\n活动覆盖全体服刑人员。"
def test_brief(): d = classify(read_text(BRIEF)); assert d.kind == "brief" and [b.t for b in d.blocks] == ["title","body","h1","body"]

def test_long_numbered_is_body():   # 一、 开头、> 50 字、以“。”结尾 → body
def test_second_line_with_period_not_title():   # 第 2 行以“。”结尾 → body
def test_inline_attachment():        # "附件：《评估报告模板》" → 单个 attachment，text="《评估报告模板》"
def test_attachment_zone_ends():     # 附件项后接无序号段落 → body
def test_irregular_numbering():      # Review Focus 2
    ts = [b.t for b in classify(read_text("标题\n　　一 、甲\n(一)乙\n（二)丙\n1．丁")).blocks]
    assert ts == ["title","h1","h2","h2","h3"]
def test_table_first_and_single_line():   # Review Focus 3
    d = classify([Block("table", rows=[["a"]]), Block("body", "标题")])
    assert [b.t for b in d.blocks] == ["table","title"]
    assert [b.t for b in classify(read_text("只有一行")).blocks] == ["title"]
def test_signer_requires_date():     # 末尾无日期 → 短句不判为落款
```

- [ ] **Step 2: 运行确认失败** — `python -m pytest tests/gongwen/test_classify.py -q`
- [ ] **Step 3: 实现**
- [ ] **Step 4: 运行确认通过**
- [ ] **Step 5: Commit** — `feat(公文排版): 段落类型自动识别`

---

### Task 4: 生成单位格式 .docx

**Files:**
- Create: `gongwen/core/build.py`
- Test: `tests/gongwen/test_build.py`

**Interfaces:**
- Consumes: `Document`, `Block`, `normalize_date`, `GongwenError`
- Produces:
  - `build_docx(doc: Document, out: Path) -> Path`：排版逻辑移植 skill `gw_build.py` 的 `set_font / para / add_table / add_page_number / build` 页面与中文设置部分（原样参数），输入换成 Document：
    - 依次输出：所有 `title`（居中 22pt 方正小标宋）；`brief` 时再加一个空段；然后按原顺序输出其余块，**跳过** `attachment/signer/date`；`addressee` 顶格黑体；`h1` 黑体；`h2` 楷体；`h3/body` 仿宋；`table` 用 add_table。
    - 其后若有 `attachment`：一段“附件”+ 每项 `f"{i}、{text}"`（首行缩进）。
    - 其后若有 `signer` 或 `date`：一个右对齐空段，再输出 signer、`normalize_date(date)`，右对齐。
  - `default_filename(doc: Document) -> str`：见 Global Constraints。

- [ ] **Step 1: 写失败测试**（导出后用 python-docx 读回）

```python
def test_fonts_and_sizes(tmp_path):   # 对 NOTICE 的 classify 结果导出
    ps = docx.Document(out).paragraphs
    assert font(ps[0]) == ("方正小标宋简体", 22) and ps[0].alignment == CENTER
    assert font(ps[2]) == ("黑体", 16) and first_line_chars(ps[2]) is None       # 主送机关顶格
    assert font(h1) == ("黑体", 16) and font(h2) == ("楷体_GB2312", 16) and font(body) == ("仿宋_GB2312", 16)
    assert first_line_chars(body) == "200"
    assert all(p.paragraph_format.line_spacing == Pt(26) and p.paragraph_format.space_after == Pt(8) for p in ps)
    assert not any(r.bold for p in ps for r in p.runs)
def test_four_font_slots(tmp_path):    # 每个 run 的 rFonts 四槽相同
def test_page_setup(tmp_path):         # 边距 Cm 2.54/3.17，页眉 1.5，页脚 1.75，docGrid lines/312，页脚含 PAGE 域
def test_attachments_and_signoff(tmp_path):
    texts = [p.text for p in ps]
    assert texts[-6:] == ["附件", "1、《罪犯再犯风险评估量表（成年男犯）》及填写说明", "2、《评估报告模板》", "", "评估矫治中心", "2026年8月24日"]
    assert ps[-1].alignment == RIGHT
def test_brief_blank_after_title(tmp_path):  # brief: ps[1].text == ""；notice: ps[1] 为标题第二行
def test_table(tmp_path):              # Table Grid、居中、表头黑体 14pt、内容仿宋 14pt，表后空段
def test_default_filename():           # Review Focus 5
    assert default_filename(Document("notice", [Block("title", "关于“A/B”的"), Block("title", "通知")])) == "关于“AB”的通知.docx"
    assert default_filename(Document("brief", [Block("body", "x")])) == "公文.docx"
```

（`font(p)` 取第一个 run 的 `rFonts eastAsia` 与 `font.size.pt`；`first_line_chars(p)` 读 `w:ind/@w:firstLineChars`。这些 helper 写在测试文件里。）

- [ ] **Step 2: 运行确认失败** — `python -m pytest tests/gongwen/test_build.py -q`
- [ ] **Step 3: 实现**
- [ ] **Step 4: 运行确认通过**；再用 `soffice --headless --convert-to pdf` 转一份 NOTICE 输出并转 PNG 看一眼版面（本地有 LibreOffice，字体为近似字体）。
- [ ] **Step 5: Commit** — `feat(公文排版): 生成单位格式 Word`

---

### Task 5: Api、日志、入口与自检

**Files:**
- Create: `gongwen/api.py`, `gongwen/logging_setup.py`, `gongwen/main.py`
- Test: `tests/gongwen/test_api.py`

**Interfaces:**
- Consumes: `read_docx`, `read_text`, `classify`, `build_docx`, `default_filename`, `Document`, `GongwenError`
- Produces（JS 调用；所有方法返回 dict，不向 JS 抛异常）：
  - `Api.attach(window)`；窗口存为 `self._window`。
  - `open_docx(path: str) -> dict` → `{"doc": Document.to_dict()}` 或 `{"error": 中文}`
  - `parse_text(text: str) -> dict` → 同上
  - `pick_docx() -> str | None`：`FileDialog.OPEN`，`file_types=("Word 文档 (*.docx;*.doc)",)`
  - `export(doc: dict) -> dict`：`FileDialog.SAVE`，`save_filename=default_filename(...)`；取消 → `{"cancelled": True}`；否则调用 `export_to`
  - `export_to(doc: dict, path: str) -> dict` → `{"path": str}` 或 `{"error": ...}`；`PermissionError` → `"文件正在被其他程序使用，请先关闭它或换个文件名"`；`GongwenError` → 其消息；其他异常 → `logging.error(..., exc_info=e)` 后 `f"操作失败：{type(e).__name__}"`
  - `open_file(path: str) -> None`：Windows `os.startfile`，其他 `xdg-open`
  - `setup_logging() -> Path`：`logging.basicConfig(..., force=True)`
  - `main(argv) -> int`：`--selftest` → Windows 上先 `import clr`，再 `build_docx(classify(read_text(SAMPLE)))` 到临时目录并读回确认第一段字体为方正小标宋简体，写 `OK`/`FAIL: ...` 到 `GW_SELFTEST_LOG` 或 `<exe 目录>/selftest.log`，返回 0/1；否则启动窗口：标题“公文排版”，1200×760，最小 960×600，拖放用 DOMEventHandler（同文件转换器）取第一个 `pywebviewFullPath` 调 `window.loadPath(path)`。入口文件开头同文件转换器那样在非包运行时把仓库根加入 `sys.path`。

- [ ] **Step 1: 写失败测试**

```python
def test_parse_text(): assert Api().parse_text(NOTICE)["doc"]["kind"] == "notice"
def test_open_docx_error(tmp_path): assert "已损坏" in Api().open_docx(str(bad))["error"]
def test_export_to(tmp_path): r = Api().export_to(doc_dict, str(tmp_path / "通知.docx")); assert Path(r["path"]).is_file()
def test_export_permission(monkeypatch, tmp_path):   # Review Focus 4
    monkeypatch.setattr(api_mod, "build_docx", raise_(PermissionError()))
    assert Api().export_to(doc_dict, str(tmp_path / "a.docx")) == {"error": "文件正在被其他程序使用，请先关闭它或换个文件名"}
def test_export_unexpected(monkeypatch, tmp_path): ... == {"error": "操作失败：ValueError"}
def test_invalid_doc_dict(): assert "error" in Api().export_to({"kind": "x", "blocks": []}, "a.docx")
def test_log_written(monkeypatch, tmp_path): # 同文件转换器 test_log_file_written
def test_selftest(monkeypatch, tmp_path): monkeypatch.setenv("GW_SELFTEST_LOG", ...); assert main(["--selftest"]) == 0 and log == "OK"
```

- [ ] **Step 2: 运行确认失败** — `python -m pytest tests/gongwen/test_api.py -q`
- [ ] **Step 3: 实现**
- [ ] **Step 4: 运行全部测试通过** — `python -m pytest -q`
- [ ] **Step 5: Commit** — `feat(公文排版): 接口、日志与入口`

---

### Task 6: 界面

**Files:**
- Create: `gongwen/web/index.html`, `gongwen/web/style.css`, `gongwen/web/app.js`, `tools/gongwen_ui_smoke.py`

**Interfaces:**
- Consumes: `window.pywebview.api.{open_docx,parse_text,pick_docx,export,open_file}`；后端调用的全局 `window.loadPath(path)`。
- 状态：`state = {doc: {kind, blocks}|null, selected: index|null, busy}`。

布局按 spec 3.6：
- 顶栏：「打开 Word」（pick_docx → open_docx）、「粘贴文字」（弹层：textarea + 「识别」「取消」）、文种单选（notice=通知 / brief=信息简报）、「导出 Word」（无内容时禁用）。错误/成功用顶栏下方提示条（成功带「打开文件」按钮）。
- 左栏：每块一行：`<select>`（中文标签：标题、主送机关、一级标题、二级标题、三级标题、正文、附件、落款、日期）+ `contenteditable` 文字 + ×。表格行显示“表格（N 行 × M 列）”，无下拉。空状态文案“打开一份 Word，或粘贴文字开始”。
- 右栏预览：一张 A4 纸（`width:210mm; padding:25.4mm 31.7mm; box-sizing:border-box`），按容器宽度 `transform: scale()` 缩放。段落样式与导出一致：`font-size:16pt; line-height:26pt; margin:0 0 8pt; text-align:justify; text-indent:2em`；标题 22pt 居中无缩进；主送机关无缩进；落款/日期右对齐无缩进且前空一行；附件区与 build 同序（正文后，“附件”+编号）；brief 标题后空一行；表格 14pt 全框线。字体栈：`"方正小标宋简体","FZXiaoBiaoSong-B05S",serif`；`"仿宋_GB2312","FangSong_GB2312","仿宋","FangSong",serif`；`"楷体_GB2312","KaiTi_GB2312","楷体","KaiTi",serif`；`"黑体","SimHei",sans-serif`。日期预览同样做中文数字 → 阿拉伯数字（JS 版 normalize，与 Python 规则一致）。
- 交互：改类型/文字/删除/切文种 → 立即重绘预览；点左栏某行 → 预览对应段 `.hl` 高亮并 `scrollIntoView({block:"nearest"})`。

- [ ] **Step 1: 写冒烟脚本**（Playwright，`executable_path='/opt/pw-browsers/chromium'`，假后端：`parse_text` 返回固定 NOTICE 文档，`export` 记录参数并返回 `{"path":"C:/a/通知.docx"}`）检查：
  - 初始空状态文案可见、导出按钮禁用；
  - 粘贴文字 → 左栏 12 行；预览第一段 `font-family` 含“方正小标宋简体”；
  - 把第 5 行（h1）改成“正文” → 预览对应段 `font-family` 含“仿宋_GB2312”；
  - 删除一行后左栏 11 行；切到“信息简报”→ 预览标题后出现空段；
  - 预览末两段文字为“评估矫治中心”“2026年8月24日”，且右对齐；
  - 导出 → 假后端收到的 doc 与当前状态一致；提示条出现「打开文件」；
  - 960×600 下无横向滚动；保存截图 `docs/screenshots/gongwen.png`。
- [ ] **Step 2: 运行确认失败**（页面不存在）— `python tools/gongwen_ui_smoke.py /home/user/PDF`
- [ ] **Step 3: 实现三个文件**
- [ ] **Step 4: 运行确认通过**，查看截图。
- [ ] **Step 5: Commit** — `feat(公文排版): 界面`

---

### Task 7: 打包与发布

**Files:**
- Create: `build/gongwen.spec`, `.github/workflows/build-gongwen.yml`
- Modify: `README.md`（追加「公文排版」一节：功能、下载、使用、开发命令）

**Interfaces:**
- Consumes: `gongwen/main.py` 的 `main()` / `--selftest`；`build/app.exe.config`。

要点：
- spec：入口 `gongwen/main.py`；datas `gongwen/web → gongwen/web`；`collect_all("webview")`、`collect_all("docx")`（python-docx 默认模板）；`console=False`；`name="公文排版"`；onedir。
- workflow（push 到 main 与 `claude/**`、手动触发；windows-latest，Python 3.12）：
  1. `pip install python-docx pywebview pytest pyinstaller` → `python -m pytest tests/gongwen -v`
  2. `pyinstaller build/gongwen.spec --distpath build/dist --workpath build/work --noconfirm`；`Copy-Item build/app.exe.config "build/dist/公文排版/公文排版.exe.config"`
  3. 给 `_internal` 下所有 .dll 写 `Zone.Identifier`（ZoneId=3）—— 同 build-windows.yml
  4. `Start-Process ... --selftest -Wait -PassThru`，退出码 0 且 `selftest.log` 为 `OK`
  5. `Compress-Archive` → `公文排版-windows.zip`，upload-artifact（30 天）
- 现有 `test.yml` 跑全部 pytest，自动覆盖 `tests/gongwen`；gongwen 测试与核心代码不 import webview，无需改它的依赖。

- [ ] **Step 1: 写 spec、workflow、README**
- [ ] **Step 2: 本地验证** —— `python -m pytest -q` 全过；yaml 可解析；本地 `pyinstaller build/gongwen.spec` 后 `build/dist/公文排版/公文排版 --selftest` 返回 0、log 为 OK。
- [ ] **Step 3: Commit、push**，在 GitHub 查看 build-gongwen 运行结果，失败则读日志修复，直到自检通过并产出 zip。
