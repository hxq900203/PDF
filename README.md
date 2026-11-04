# 文件转换器

Windows 桌面软件，在 **Word / PDF / PNG / Excel** 之间互相转换，全部离线在本机完成。LibreOffice 已随软件打包，解压即用。

## 支持的转换（第一版）

| 输入 ↓ / 输出 → | PDF | Word | PNG | Excel |
|---|---|---|---|---|
| Word (.docx/.doc) | ✅ | — | ✅ | — |
| Excel (.xlsx/.xls) | ✅ | — | ✅ | — |
| PDF | — | ✅ | ✅（每页一张） | ✅（提取表格） |
| 图片 (.png/.jpg) | ✅（可合并为一个 PDF） | — | — | — |

## 下载

GitHub → **Actions** → 最新一次成功的 **build-windows** → 页面底部 **Artifacts** 下载 `文件转换器-windows`，解压后双击 `文件转换器/文件转换器.exe`。

需要 Windows 10/11（系统自带 Edge WebView2）。

## 使用

1. 把文件拖进窗口，或点击添加。
2. 选择要转换成的格式（只显示所选文件都支持的格式）。
3. 选择保存位置（默认和原文件同目录），点「开始转换」。

输出不会覆盖已有文件，重名时自动命名为 `报告 (1).pdf`。

## 开发

```bash
pip install -r requirements-dev.txt
python -m pytest          # 需要 LibreOffice 的测试在没有 soffice 时自动跳过
python -m app.main        # 启动界面
python -m app.main --selftest
```

- 日志：`%LOCALAPPDATA%\文件转换器\logs\app.log`
- 设计文档：`docs/superpowers/specs/2026-10-15-file-converter-design.md`

---

# 公文排版

单独的 Windows 桌面软件：把已有 Word 或粘贴的文字，一键排成本单位公文格式（方正小标宋标题、仿宋_GB2312 正文、黑体 / 楷体层级标题，固定行距 26 磅），先预览、可修改，再导出 .docx。

## 下载

GitHub → **Actions** → 最新一次成功的 **build-gongwen** → 页面底部 **Artifacts** 下载 `公文排版-windows`，解压后双击 `公文排版/公文排版.exe`。

## 使用

1. 点「打开 Word」或把 .docx 拖进窗口；也可以点「粘贴文字」。
2. 左侧每段旁边是自动识别的类型（标题、主送机关、一级标题……落款、日期），认错了点一下改；文字可直接编辑，× 删除。
3. 选择文种：「通知」（标题后不空行）或「信息简报」（标题后空一行）。
4. 右侧是 A4 实时预览，确认后点「导出 Word」，默认文件名为标题。

老版 .doc 请先用「文件转换器」转为 .docx，或复制文字后粘贴。

## 开发

```bash
pip install python-docx pywebview pytest
python -m pytest tests/gongwen --confcutdir=tests/gongwen
python -m gongwen.main            # 启动界面
python -m gongwen.main --selftest
```

- 日志：`%LOCALAPPDATA%\公文排版\logs\app.log`
- 设计文档：`docs/superpowers/specs/2026-11-04-gongwen-formatter-design.md`

---

# 公文排版 网页版（UOS / 离线）

给不能联网的电脑（如 UOS 20 龙芯）用的版本：一个 `公文排版.html` 文件，用浏览器打开即可，不需要安装，也不联网。功能与 Windows 版相同。

## 拷贝与打开

1. 在能上网的电脑上获取 `公文排版.html`（GitHub → Actions → 最新一次成功的 **build-gongwen-web** → Artifacts 里的 `公文排版-网页版`）。
2. 用 U 盘拷到单位电脑，双击用浏览器打开。

## 使用

- 「打开 Word」或把 .docx 拖进页面；也可以「粘贴文字」。
- 左侧改类型、改文字、删段；右侧 A4 实时预览；选择文种后点「导出 Word」，文件保存到浏览器的「下载」文件夹，文件名为标题。
- 第一次使用请点「自检」：检查生成 Word 是否正常、四种公文字体是否已安装，并显示浏览器信息。

## 缺字体时

- 预览自动用相似字体显示（如 仿宋_GB2312 → 仿宋 → 方正仿宋_GBK → 华文仿宋 → 思源宋体）。
- 默认导出的 Word 仍使用规定字体，并附带替代提示；拿到装有规定字体的电脑上打开即为标准格式。
- 勾选「缺字体时用本机替代字体（仅适合本机打印）」后，导出时把本机缺少的规定字体换成本机已有的相似字体。

## 开发

```bash
cd gongwen-web && npm ci && npm test && cd ..
python -m pytest tests/gongwen_web --confcutdir=tests/gongwen_web   # 与 Python 版逐项比对
python gongwen-web/build.py                                          # 生成 gongwen-web/dist/公文排版.html
python tools/gongwen_web_smoke.py .                                  # 界面冒烟测试
```
