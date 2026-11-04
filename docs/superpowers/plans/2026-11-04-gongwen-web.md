# 公文排版 网页版 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 单文件 `公文排版.html`，离线在 UOS 自带浏览器中完成 读入 → 识别 → 预览修改 → 导出，结果与 Python 版一致，并支持缺字体替代。

**Architecture:** `gongwen-web/src/*.js` 为普通脚本（非 ES 模块），都挂在全局 `GW` 上；`build.py` 把 CSS、JSZip、src 依序内联成 `dist/公文排版.html`。测试：Node 用 `vm` 加载同样的源码（注入 xmldom 的 DOMParser）跑单元测试；pytest 通过 `node gongwen-web/tests/cli.js` 调 JS 核心，与 Python `gongwen.core` 逐项比对；Playwright 在 `file://` 下测界面。

**Tech Stack:** ES2017 JavaScript，JSZip 3.10.1（vendored），Node 22（仅测试/构建），@xmldom/xmldom（仅测试），Python 3 + python-docx（比对、构建脚本），Playwright。

**Spec:** `docs/superpowers/specs/2026-11-04-gongwen-web-design.md`

## Global Constraints

- 源码只用 ES2017：禁止 `?.`、`??`、`**=`、类字段、`import`/`export`、顶层 await、正则 lookbehind `(?<`、命名捕获组 `(?<name>`。构建脚本做正则检查，命中即失败。
- 浏览器 API 仅限：DOMParser、XMLSerializer、Blob、FileReader、URL.createObjectURL、canvas measureText、`a[download]`。XML 访问只用 DOM Level 2（`getElementsByTagNameNS`、`childNodes`、`localName`、`namespaceURI`、`getAttributeNS`、`setAttributeNS`），不用 querySelector（xmldom 不支持）。
- 页面运行时零网络请求；所有资源内联。
- 每个 src 文件格式：`var GW = GW || {};\n(function (GW) { "use strict"; ... })(GW);`
- 规则、阈值、格式参数、错误文案与 Python 版完全一致（SHORT 30、TITLE_MAX 40、SIGNER_MAX 20、H_MAX 50；文案见 `gongwen/core/*.py`）。
- 替代字体表（spec 5A）：
  - 方正小标宋简体: 方正小标宋_GBK, 华文中宋, 宋体, Source Han Serif SC, Noto Serif CJK SC
  - 仿宋_GB2312: 仿宋, 方正仿宋_GBK, 华文仿宋, Source Han Serif SC, Noto Serif CJK SC
  - 楷体_GB2312: 楷体, 方正楷体_GBK, 华文楷体, Source Han Serif SC, Noto Serif CJK SC
  - 黑体: 方正黑体_GBK, Source Han Sans SC, Noto Sans CJK SC
  - 「加粗补偿」集合：宋体, Source Han Serif SC, Noto Serif CJK SC（替代方正小标宋简体时标题加粗）
- 产物：`gongwen-web/dist/公文排版.html`（不提交）；CI artifact 名 `公文排版-网页版`。

## Review Focus

1. **老浏览器语法**：合并后的源码里混入 ES2020+ 语法，在旧 Chromium 上整页白屏 → 构建脚本拦截。Task 1 加测试（构建脚本对含 `a?.b` 的源码报错）。
2. **file:// 下下载与拖放**：双击打开的页面里导出按钮能触发下载、拖入 .docx 能读取（无 fetch/模块加载）。Task 6 冒烟测试在 `file://` 下拦截下载并校验内容。
3. **大文件 / 多页文档**：30 页、上千段的 .docx 读入和预览不卡死（< 3 秒）。Task 6 冒烟测试用 1500 段文档计时。
4. **JS 与 Python 生成的 XML 细节不一致**（如 firstLineChars、docGrid、compat、页码域）→ WPS 显示不同。Task 4 比对测试逐项覆盖。
5. **字体检测误判导致勾选导出写错字体名**：只有检测为“未找到”的字体才替换；全部已安装时勾选导出与默认导出完全相同。Task 5 加测试。

---

## 文件结构

```
gongwen-web/
├─ package.json            devDependencies: @xmldom/xmldom（测试用）；scripts.test
├─ vendor/jszip.min.js     JSZip 3.10.1（npm 包 dist/jszip.min.js，保留许可证注释）
├─ src/dates.js  model.js  classify.js  numbering.js  reader.js  build.js  fonts.js  selftest.js  ui.js
├─ src/index.html  src/style.css
├─ build.py                合并 + ES2017 语法检查 → dist/公文排版.html
└─ tests/
   ├─ load.js              vm 加载 vendor + src 核心（不含 ui.js），注入 DOMParser/XMLSerializer，返回 GW
   ├─ cli.js               node cli.js read <docx> | classify <txt> | build <doc.json> <out.docx> [substitutes.json]
   └─ *.test.js            node --test 单元测试
tests/gongwen_web/         pytest：JS 与 Python 比对（--confcutdir=tests/gongwen_web）
tools/gongwen_web_smoke.py Playwright 冒烟
.github/workflows/build-gongwen-web.yml
```

---

### Task 1: 骨架、加载器、构建脚本、日期与模型

**Files:**
- Create: `gongwen-web/package.json`, `gongwen-web/vendor/jszip.min.js`, `gongwen-web/src/dates.js`, `gongwen-web/src/model.js`, `gongwen-web/tests/load.js`, `gongwen-web/build.py`, `gongwen-web/src/index.html`（最小骨架）, `gongwen-web/src/style.css`（暂空）
- Test: `gongwen-web/tests/dates.test.js`, `gongwen-web/tests/model.test.js`, `tests/gongwen_web/test_gw_web_build_script.py`
- Modify: `.gitignore`（加 `gongwen-web/dist/`、`gongwen-web/node_modules/`）

**Interfaces:**
- Produces:
  - `GW.normalizeDate(s: string) -> string`（同 Python，含 ○ Ｏ ０）
  - `GW.TYPES`, `GW.KINDS`, `GW.cleanText(s)`（去 `[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]`）
  - `GW.GWError`（`function GWError(msg)`，原型继承 Error，`name = "GWError"`）
  - `GW.validateDoc(d) -> {kind, blocks}`：类型/文种非法抛 GWError（“段落类型无效”/“文种无效”），文字经 cleanText
  - `load.js`：`module.exports = function load(files = CORE) -> GW`；CORE = `["dates","model","classify","numbering","reader","build","fonts"]` 中**已存在**的文件依序加载
  - `build.py`：`python gongwen-web/build.py [--out PATH]`；按顺序内联 `style.css`、`vendor/jszip.min.js`、`dates model classify numbering reader build fonts selftest ui`（存在的才内联）进 `index.html` 的 `<!--STYLE-->`、`<!--SCRIPTS-->` 占位；对非 vendor 源码做 ES2017 检查，命中则打印文件与行号并退出码 1。

- [ ] **Step 1:** `cd gongwen-web && npm install --save-dev @xmldom/xmldom jszip@3.10.1`，把 `node_modules/jszip/dist/jszip.min.js` 复制到 `vendor/`（jszip 不留在依赖里：随后 `npm uninstall jszip`）。
- [ ] **Step 2: 写失败测试**
  - dates.test.js：与 `tests/gongwen/test_gw_dates.py` + `test_circle_zero_dates` 相同的参数表。
  - model.test.js：`validateDoc({kind:"x",blocks:[]})` 抛“文种无效”；`{t:"xx"}` 抛“段落类型无效”；`cleanText("标\x01题") === "标题"`。
  - test_gw_web_build_script.py：`build.py` 生成文件存在且含 `<script>`、不含 `src=`/`href=`；在临时 src 副本里写入含 `a?.b` 的 js，`build.py` 退出码 1 且输出含文件名。
- [ ] **Step 3: 运行确认失败** — `cd gongwen-web && node --test tests/`；`python -m pytest tests/gongwen_web -q --confcutdir=tests/gongwen_web`
- [ ] **Step 4: 实现**
- [ ] **Step 5: 运行确认通过**
- [ ] **Step 6: Commit** — `feat(公文排版网页版): 骨架、构建脚本、日期与模型`

---

### Task 2: 识别（classify.js）

**Files:** Create `gongwen-web/src/classify.js`；Test `gongwen-web/tests/classify.test.js`, `tests/gongwen_web/test_gw_web_classify.py`

**Interfaces:**
- Consumes: `GW.cleanText`
- Produces: `GW.readText(text) -> blocks`（拆行规则同 Python `_clean_lines`：`/\r\n|[\r\n\v\f\x85  ]/`，去控制字符，strip `" \t　\xa0"`，丢空行；空则抛 GWError“没有读到任何文字”）；`GW.classify(blocks) -> {kind, blocks}`，逐条移植 `gongwen/core/classify.py`（正则相同；`H3` 的 `(?!\d)` 是 lookahead，允许）。
- `cli.js classify <txtfile>` 输出 `JSON.stringify(GW.classify(GW.readText(text)))`。

- [ ] **Step 1: 写失败测试**
  - classify.test.js：移植 `tests/gongwen/test_gw_classify.py` 全部用例和 `test_gw_review_fixes.py` 中识别用例（inline_numbered_attachment、single_unnumbered_attachment、circle_zero_dates 的识别部分、control_chars 拆行），期望值原样。
  - test_gw_web_classify.py：对 `samples.NOTICE`、`samples.BRIEF` 及 10 条边界文本（与 Python 测试同），`node cli.js classify` 的 JSON 与 `classify(read_text(...)).to_dict()` 完全相等。
- [ ] **Step 2: 确认失败** → **Step 3: 实现** → **Step 4: 确认通过**
- [ ] **Step 5: Commit** — `feat(公文排版网页版): 段落识别`

---

### Task 3: 读入 .docx（numbering.js、reader.js）

**Files:** Create `gongwen-web/src/numbering.js`, `gongwen-web/src/reader.js`；Test `gongwen-web/tests/numbering.test.js`, `tests/gongwen_web/test_gw_web_reader.py`

**Interfaces:**
- Consumes: JSZip、DOMParser、`GW.readText` 的拆行函数（导出为 `GW._cleanLines`）
- Produces:
  - `GW.formatNumber(n, fmt) -> string`（同 `numbering.format_number`）
  - `GW.Numbering(numberingDoc | null, stylesDoc | null)`，方法 `prefix(pElement) -> string`（同 Python 计数与 startOverride、样式继承规则）
  - `GW.readDocx(arrayBuffer, filename) -> Promise<blocks>`：`.doc` 后缀、打不开、空文档的报错文案同 Python；文字提取同 `_para_text`（w:t / w:tab→`\t` / w:br、w:cr→`\n`；祖先为 w:del、w:txbxContent、mc:Fallback 的跳过）；body 遍历同 `_walk`（w:p、w:tbl、w:sdt/w:sdtContent、w:customXml）；表格每格 = 该格内所有 w:p 文字用 `\n` 连接后 `_cleanLines` 再 `\n` 连接；合并单元格按 w:gridSpan 重复、w:vMerge continue 取上方单元格文字（与 python-docx `row.cells` 一致）；全空表格丢弃。
- `cli.js read <docx>` 输出 blocks JSON。

- [ ] **Step 1: 写失败测试**
  - numbering.test.js：`formatNumber` 对 chineseCounting 1/10/11/20/24、decimalEnclosedCircle 3、upperLetter 28、bullet、未知格式。
  - test_gw_web_reader.py：用 `tests/gongwen/test_gw_reader.py`、`test_gw_review_fixes.py` 的 python-docx 构造方式在 tmp_path 生成：段落+表格、软换行、自动编号（_numbered_doc）、修订插入/删除+内容控件、分页符、嵌套表格、横向合并单元格（`a.merge(b)`）、纵向合并单元格；对每个文件 `node cli.js read` 的 JSON == `[b.to_dict() for b in read_docx(p)]`。错误用例（.doc、损坏、空文档）：cli 退出码 2，stderr 为与 Python 相同的中文消息。
- [ ] **Step 2: 确认失败** → **Step 3: 实现** → **Step 4: 确认通过**
- [ ] **Step 5: Commit** — `feat(公文排版网页版): 读入 Word`

---

### Task 4: 生成 .docx（build.js，默认导出）

**Files:** Create `gongwen-web/src/build.js`；Test `tests/gongwen_web/test_gw_web_build.py`, `gongwen-web/tests/build.test.js`

**Interfaces:**
- Consumes: JSZip、`GW.normalizeDate`、`GW.validateDoc`
- Produces:
  - `GW.buildDocx(doc, opts) -> Promise<Uint8Array>`；`opts.substitutes`（Task 5 使用，默认 `{}`）
  - `GW.defaultFilename(doc) -> string`（同 Python：去 `\/:*?"<>|` 与 `[\x00-\x1f\x7f]`，截 80 字，去末尾点和空格，空为“公文”）
  - 输出部件：`[Content_Types].xml`、`_rels/.rels`、`word/document.xml`、`word/styles.xml`、`word/settings.xml`、`word/fontTable.xml`、`word/footer1.xml`、`word/_rels/document.xml.rels`、`docProps/core.xml`、`docProps/app.xml`。
  - document.xml 的段落/表格/页面属性逐项对齐 Python 输出：段落 `w:spacing w:before="0" w:after="160" w:line="520" w:lineRule="exact"`；缩进 `w:ind w:firstLine="640" w:firstLineChars="200"`；run `w:rFonts` 四槽 + `w:hint="eastAsia"`、`w:b w:val="0"`、`w:sz`/`w:szCs`（22pt→44，16pt→32，14pt→28，9pt→18）；sectPr：pgSz 11906×16838，pgMar top/bottom 1440、left/right 1797、header 850、footer 992，docGrid type=lines linePitch=312，footerReference；表格 `w:tblStyle w:val="TableGrid"`（styles.xml 中定义全框线 TableGrid）、`w:jc center`、单元格 vAlign center、段落 jc center、spacing after 0、line 240 auto。精确数值以 Python 生成文件的 XML 为准（实施时先 `unzip -p` 查看 Python 输出再写）。
  - styles.xml：Normal 字体四槽 仿宋_GB2312、sz 32；docDefaults rPr 含 `w:kern w:val="2"`、`w:lang w:eastAsia="zh-CN"`。
  - settings.xml：compat 六项 + compatSetting compatibilityMode 15，characterSpacingControl compressPunctuation。
  - fontTable.xml（spec 5A 默认导出）：四种规定字体各一个 `w:font`，含 `w:altName`（替代表第一项）、`w:charset w:val="86"`、`w:family`（小标宋/仿宋/楷体 roman，黑体 swiss）。
- `cli.js build <doc.json> <out.docx> [subs.json]`。

- [ ] **Step 1: 写失败测试**
  - test_gw_web_build.py：对 NOTICE、BRIEF、含表格文档三份 Document：Python `build_docx` 与 `node cli.js build` 各生成一份，python-docx 读回后逐段比较 `(text, 四槽字体, size, bold, alignment, firstLineChars, firstLine, line_spacing, line_spacing_rule, space_before, space_after)`；sections 的 page_width/height、四边距、header/footer_distance、docGrid type/linePitch；页脚段落对齐与是否含 `PAGE` 域；表格 style 名为 “Table Grid”、每格 (text, font, size, alignment)。全部相等。
  - 同文件中：JS 输出的 fontTable.xml 含 `方正小标宋简体` 且其 `w:altName` 为 `方正小标宋_GBK`，`黑体` 的 family 为 `swiss`。
  - 同文件中（需 soffice）：`soffice --headless --convert-to pdf` JS 输出成功，PDF 第一页文本含标题。
  - build.test.js：`defaultFilename` 与 Python `test_default_filename`、`test_filename_control_chars_length_and_dots` 同用例。
- [ ] **Step 2: 确认失败** → **Step 3: 实现** → **Step 4: 确认通过**
- [ ] **Step 5: Commit** — `feat(公文排版网页版): 生成 Word`

---

### Task 5: 缺字体替代、字体检测、自检

**Files:** Create `gongwen-web/src/fonts.js`, `gongwen-web/src/selftest.js`；Modify `gongwen-web/src/build.js`；Test `gongwen-web/tests/fonts.test.js`, `tests/gongwen_web/test_gw_web_substitute.py`

**Interfaces:**
- Produces:
  - `GW.FALLBACKS`（Global Constraints 表）、`GW.BOLD_COMPENSATE`
  - `GW.chooseSubstitutes(detect: {font: bool}) -> {required: substitute}`：对每个规定字体，若 `detect[required]` 为 false，取 FALLBACKS 中第一个 `detect[x] === true` 的；都没有则不替换。纯函数，可在 Node 测。
  - `GW.detectFonts() -> {name: bool}`（浏览器）：对规定字体与所有替代字体，用 canvas 比较 `"<name>", monospace` 与 `monospace`、`"<name>", serif` 与 `serif` 绘制 `"测试文字永和ABCabc123"` 的宽度，任一不同视为已安装。
  - `GW.cssStack(required) -> string`：`'"规定", "替代1", ..., serif|sans-serif'`（黑体为 sans-serif）。
  - `buildDocx(doc, {substitutes})`：对 substitutes 中的规定字体，run 四槽写替代名；若被替代的是方正小标宋简体且替代名在 BOLD_COMPENSATE，标题 run 写 `w:b`（不写 `w:val="0"`）。
  - `GW.runSelftest() -> Promise<[{name, ok, detail}]>`（浏览器）：三项（生成读回 / 字体 / 浏览器信息），文案见 spec 第 5 节与 5A。
- [ ] **Step 1: 写失败测试**
  - fonts.test.js：`chooseSubstitutes({"方正小标宋简体":false,"华文中宋":false,"宋体":true, "仿宋_GB2312":true,"楷体_GB2312":false,"楷体":true,"黑体":true})` → `{"方正小标宋简体":"宋体","楷体_GB2312":"楷体"}`；全部 true → `{}`（Review Focus 5）；全部 false → `{}`。`cssStack("黑体")` 以 `sans-serif` 结尾。
  - test_gw_web_substitute.py：`subs = {"方正小标宋简体":"宋体","仿宋_GB2312":"仿宋"}` 导出 NOTICE：标题 run 四槽为“宋体”且 bold 为 True；正文四槽为“仿宋”；h1 仍为“黑体”、h2 仍为“楷体_GB2312”；行距、缩进、页面设置与默认导出逐项相同。`subs = {}` 时与默认导出的 document.xml 字节完全相同。
- [ ] **Step 2: 确认失败** → **Step 3: 实现** → **Step 4: 确认通过**
- [ ] **Step 5: Commit** — `feat(公文排版网页版): 缺字体替代与自检`

---

### Task 6: 界面与单文件构建

**Files:** Create/Modify `gongwen-web/src/index.html`, `gongwen-web/src/style.css`, `gongwen-web/src/ui.js`；Create `tools/gongwen_web_smoke.py`

**Interfaces:**
- Consumes: 全部 `GW.*`
- 由 `gongwen/web/` 改写：顶栏「打开 Word」（隐藏 `<input type=file accept=".docx,.doc">`）、「粘贴文字」、文种、复选框「缺字体时用本机替代字体（仅适合本机打印）」、「导出 Word」、「自检」。拖放：`drop` 事件取 `dataTransfer.files[0]`，FileReader 读为 ArrayBuffer。导出：`buildDocx(doc, {substitutes: 勾选 ? chooseSubstitutes(detectFonts()) : {}})` → Blob（`application/vnd.openxmlformats-officedocument.wordprocessingml.document`）→ 临时 `a[download=defaultFilename]` 点击 → 提示条“已保存到下载文件夹：<文件名>”（有替代时追加“已使用替代字体：A→B …”）。`beforeunload`：有内容且有未导出修改时 `e.returnValue = ""`。预览字体用 `GW.cssStack`（在 `:root` 设 CSS 变量），方正小标宋简体检测为缺失且实际替代在 BOLD_COMPENSATE 时预览标题加粗。自检弹窗列出 runSelftest 结果。其余交互与 Windows 版相同（含回车/粘贴单行化、点击高亮、改类型/编辑/删除/切文种即时刷新）。
- [ ] **Step 1: 写冒烟脚本**（先 `python gongwen-web/build.py`；Playwright `file://` 打开 dist；`page.on("request")` 记录所有非 `file:`/`data:`/`blob:` 请求）检查：
  - 空状态文案、导出禁用；
  - 用 `set_input_files` 上传 python-docx 生成的通知 .docx → 左栏行数、类型与 Python 识别一致；
  - 粘贴 NOTICE → 12 行；改类型后预览字体变化；行内回车不产生换行；删除；切换简报出现空段；
  - 导出：`page.expect_download()` 保存后用 python-docx 读回，第一段字体为方正小标宋简体，文件名为默认文件名（Review Focus 2）；
  - 勾选替代后导出成功（Chromium 无方正字体，标题应换成检测到的替代或保持原名——断言与 `chooseSubstitutes(detectFonts())` 在页面里的结果一致）；
  - 自检弹窗三项均有结果，第一项 ✅；
  - 有未导出修改时触发 beforeunload 对话框（`page.on("dialog")`）；
  - 1500 段文本粘贴后识别 + 预览渲染 < 3 秒（Review Focus 3）；
  - 网络请求数为 0；无 pageerror；960×600 无横向滚动；截图 `docs/screenshots/gongwen-web.png`。
- [ ] **Step 2: 确认失败** → **Step 3: 实现** → **Step 4: 确认通过并看截图**
- [ ] **Step 5: Commit** — `feat(公文排版网页版): 界面与单文件构建`

---

### Task 7: CI、README、交付

**Files:** Create `.github/workflows/build-gongwen-web.yml`；Modify `README.md`

- workflow（ubuntu-latest；push main 与 `claude/**`；手动）：setup-node 22、setup-python 3.12；`apt-get install -y libreoffice-writer fonts-noto-cjk`；`pip install python-docx pytest playwright`；`cd gongwen-web && npm ci && node --test tests/`；`python -m pytest tests/gongwen_web -v --confcutdir=tests/gongwen_web`；`python gongwen-web/build.py`；`python -m playwright install chromium --with-deps` 后跑 `tools/gongwen_web_smoke.py`（脚本支持环境变量 `PW_CHROMIUM` 指定可执行文件，未设时用 Playwright 自带）；upload-artifact `公文排版-网页版`（`gongwen-web/dist/公文排版.html`）。
- README：「公文排版 网页版（UOS / 离线）」一节：拷贝方式、打开方式、自检、缺字体替代勾选框、导出位置。
- [ ] **Step 1: 写 workflow 与 README** → **Step 2:** 本地全部测试 + 构建 + 冒烟通过 → **Step 3: Commit、push，确认 CI 绿，下载 artifact 发给用户**。
