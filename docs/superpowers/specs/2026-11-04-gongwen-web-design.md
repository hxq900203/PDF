# 公文排版 网页版（UOS 龙芯）设计文档

日期：2026-11-04
状态：待用户审阅

## 1. 目标

让「公文排版」在单位的 UOS 20（loongarch64，龙芯）电脑上可用。该电脑**不能联网**，浏览器为 UOS 自带浏览器（版本未知）。

做法：把公文排版做成**一个独立的 `公文排版.html`**，所有代码内嵌，双击用浏览器打开即可使用；读入、识别、预览、导出全部在浏览器本地完成。

**成功标准**

- 用 U 盘把 `公文排版.html` 拷到 UOS 电脑，双击打开即可用；无需安装、无需开发者模式、无需联网。
- 功能与 Windows 版一致：打开 .docx / 粘贴文字 → 自动识别 → 左侧改类型/文字/删段，右侧 A4 实时预览 → 导出 .docx。
- 同一份内容，网页版与 Windows 版（Python）识别结果逐块相同，导出的 .docx 在第 6 节所列各项上完全一致。
- 页面运行时不发出任何网络请求。

**不做**

- 修改或替换 Windows 版（`gongwen/` Python 版保持不变）。
- 老版 .doc、OCR、AI 代写。
- 浏览器内保存草稿（关页面即丢失，离开前提醒）。

## 2. 方案

- 核心逻辑（读入、识别、日期、生成）用 JavaScript 重写，规则与参数逐条照搬 Python 版：
  - 识别规则：`gongwen/core/classify.py`（含审查修复：附件写法、○ 日期、小数不是序号）
  - 读入：`gongwen/core/reader.py` + `numbering.py`（自动编号、修订插入、内容控件、分页符、嵌套表格、控制字符）
  - 生成：`gongwen/core/build.py`（即用户 skill 的 gw_build.py 参数）
  - 文件名：`default_filename`
- .docx 读写使用 **JSZip 3.10.1**（MIT），内嵌进 HTML，不从网络加载。
- 生成 .docx 时直接写 WordprocessingML（document.xml、styles.xml、settings.xml、footer1.xml、numbering 无需、[Content_Types].xml、rels），XML 内容对照 Python 版输出。
- **兼容老浏览器**：源码只用 ES2017 语法（不用 `?.`、`??`、类字段、顶层 await 等），只用旧版 Chromium（≥ 70）已有的 API（DOMParser、XMLSerializer、Blob、FileReader、`a[download]`）。不使用 ES 模块（`file://` 下老浏览器受限），合并为普通脚本。

## 3. 目录与构建

```
gongwen-web/
├─ src/
│  ├─ dates.js       normalizeDate
│  ├─ model.js       TYPES、KINDS、cleanText、校验
│  ├─ classify.js    classify(blocks) -> {kind, blocks}
│  ├─ reader.js      readDocx(arrayBuffer) -> Promise<blocks>、readText(text)
│  ├─ numbering.js   自动编号前缀
│  ├─ build.js       buildDocx(doc) -> Promise<Blob>、defaultFilename(doc)
│  ├─ fontcheck.js   字体检测
│  ├─ selftest.js    自检
│  ├─ ui.js          界面逻辑（由 gongwen/web/app.js 改写）
│  ├─ index.html     页面骨架
│  └─ style.css      样式（沿用 gongwen/web/style.css）
├─ vendor/jszip.min.js   JSZip 3.10.1（带许可证头）
├─ build.py          合并为 dist/公文排版.html（CSS、JSZip、各 src/*.js 依序内联）
└─ tests/            Node 运行的核心测试
```

- 核心模块同时可在 Node 中加载（文件末尾 `if (typeof module !== "undefined") module.exports = ...`），供测试使用；浏览器中挂在全局对象 `GW` 上。
- `dist/` 不提交；GitHub Actions 新增 `build-gongwen-web.yml`：运行测试 → `python gongwen-web/build.py` → 上传 `公文排版-网页版`（内含 `公文排版.html`）。

## 4. 界面（与 Windows 版的差异）

布局与 Windows 版相同（顶栏：打开 Word、粘贴文字、文种、导出 Word、自检；左栏段落列表；右栏 A4 预览）。差异：

| 操作 | 网页版 |
|---|---|
| 打开 Word | `<input type="file" accept=".docx,.doc">`；也可把 .docx 拖进页面 |
| 导出 Word | 生成 Blob，以 `a[download]` 下载，文件名 `defaultFilename(doc)`，存入浏览器「下载」文件夹 |
| 导出后 | 提示条“已保存到下载文件夹：<文件名>”；无「打开文件」按钮 |
| 离开页面 | 有内容且自上次导出后有修改时，`beforeunload` 提醒 |
| 自检 | 顶栏「自检」按钮，弹窗显示结果 |

错误提示与 Windows 版相同：“暂不支持老版 .doc 文件……”、“文件已损坏或无法读取”、“没有读到任何文字”；生成失败显示“操作失败：<错误类型>”。

## 5. 自检

弹窗列出三项，每项“✅ / ❌ + 说明”：

1. **生成与读回**：用内置示例通知 `classify(readText(示例))` → `buildDocx` → `readDocx` 读回，确认段落文字与输入一致、document.xml 中第一段字体为“方正小标宋简体”、正文行距为固定 26 磅（`w:line="520" w:lineRule="exact"`）。
2. **字体**：方正小标宋简体、仿宋_GB2312、楷体_GB2312、黑体逐个显示“已安装 / 未找到”。方法：canvas 上分别用 `"<字体>", monospace` 与 `monospace` 绘制同一段中英混排文字，宽度不同即视为已安装（再用 `serif` 复核一次）。未找到时说明：“导出的 Word 不受影响，换到装有该字体的电脑上打开即为正确格式；本机预览会用替代字体”。
3. **浏览器信息**：显示 `navigator.userAgent`，便于拍照反馈。

## 6. 一致性验证（自动测试）

- **识别**：把 `tests/gongwen/test_gw_classify.py`、`test_gw_review_fixes.py` 中的识别用例、`test_gw_dates.py` 的日期用例，用相同输入、相同期望改写为 Node 测试（`node --test`）。
- **读入**：用 Python（python-docx）生成测试 .docx（普通段落+表格、软换行、自动编号、修订插入/删除、内容控件、分页符、嵌套表格、损坏文件、空文档、.doc），Node 中 `readDocx` 的结果与 Python `read_docx` 的结果逐块相同（脚本生成期望 JSON，Node 比对）。
- **生成**：对同一组 Document（通知样例、简报样例、含表格样例），分别用 Python `build_docx` 与 JS `buildDocx` 生成 .docx，再用 python-docx 读回两份，逐段比对：文字、四个字体槽、字号、加粗、对齐、首行缩进（firstLineChars）、行距与规则、段前段后；页面尺寸、边距、页眉页脚距离、docGrid；页脚 PAGE 域；表格样式（全框线）、单元格字体字号与对齐。全部相同才算通过。
- **Word 可打开性**：JS 生成的 .docx 用 LibreOffice 无界面转 PDF 成功（CI 中运行）。
- **界面**：Playwright 打开 `dist/公文排版.html`（`file://`），覆盖：上传 .docx、粘贴、改类型、编辑、删除、切文种、导出（拦截下载，再用 python-docx 校验）、离开提醒、自检弹窗；全程监听网络请求，**必须为 0**；无 JS 报错；960×600 无横向滚动。
- **老语法检查**：构建时用正则检查合并后的源码（不含 JSZip）中没有 `?.`、`??` 等 ES2020+ 语法。

## 7. 发布

- GitHub Actions `build-gongwen-web.yml`（push 到 main、`claude/**`，手动触发）产出 `公文排版-网页版`，内含单个 `公文排版.html`。
- 构建完成后我直接把 `公文排版.html` 发给用户；用户在能上网的电脑上保存，再用 U 盘拷到 UOS 电脑。
- README 增加「公文排版 网页版（UOS / 离线）」一节。

## 8. 风险

- 无法在龙芯 UOS 实机测试。缓解：老语法约束、零网络、页面自检，用户首次使用时点自检并拍照反馈。
- 字体检测是基于宽度比较的推断，极少数情况下可能误判；只影响提示，不影响导出。
