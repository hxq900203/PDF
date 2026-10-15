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
