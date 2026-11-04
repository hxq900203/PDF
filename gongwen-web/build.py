"""把 src/ 与 vendor/ 合并成单个离线 HTML：python gongwen-web/build.py [--out PATH]"""
import argparse
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ORDER = ["dates", "model", "classify", "numbering", "reader", "build", "fonts", "selftest", "ui"]
# 老版 Chromium（≥70）不支持的语法；命中即失败，避免在 UOS 浏览器上整页白屏
MODERN = [
    (re.compile(r"\?\.(?!\d)"), "可选链 ?."),
    (re.compile(r"\?\?"), "空值合并 ??"),
    (re.compile(r"\*\*="), "**="),
    (re.compile(r"\(\?<[=!a-zA-Z]"), "正则后行断言/命名捕获组"),
    (re.compile(r"^\s*(import|export)\s"), "ES 模块 import/export"),
]


def check_syntax(name: str, code: str) -> list[str]:
    problems = []
    # 逐行粗查（不解析字符串和正则字面量），源码里避免在字符串中写出这些符号
    for lineno, line in enumerate(code.splitlines(), 1):
        stripped = line.split("//")[0]
        for pattern, label in MODERN:
            if pattern.search(stripped):
                problems.append(f"{name}:{lineno}: 使用了老浏览器不支持的语法（{label}）：{line.strip()}")
    return problems


def build(root: Path, out: Path) -> int:
    src = root / "src"
    html = (src / "index.html").read_text(encoding="utf-8")
    css = (src / "style.css").read_text(encoding="utf-8")
    scripts = [(root / "vendor" / "jszip.min.js").read_text(encoding="utf-8")]
    problems = []
    for name in ORDER:
        f = src / f"{name}.js"
        if f.exists():
            code = f.read_text(encoding="utf-8")
            problems += check_syntax(f.name, code)
            scripts.append(code)
    if problems:
        print("\n".join(problems))
        return 1
    body = "\n".join(f"<script>\n{s.replace('</script', '<\\/script')}\n</script>" for s in scripts)
    html = html.replace("<!--STYLE-->", css).replace("<!--SCRIPTS-->", body)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    print(f"已生成 {out}（{out.stat().st_size // 1024} KB）")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=HERE / "dist" / "公文排版.html")
    sys.exit(build(HERE, ap.parse_args().out))
