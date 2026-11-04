# 公文排版网页版冒烟测试：python tools/gongwen_web_smoke.py <仓库根目录>
# 需要 pip install playwright；Chromium 路径可用环境变量 PW_CHROMIUM 指定。
import os
import sys
import tempfile
import time
from pathlib import Path

import docx
from playwright.sync_api import sync_playwright

root = Path(sys.argv[1]).resolve()
sys.path[:0] = [str(root), str(root / "tests" / "gongwen")]
from samples import NOTICE  # noqa: E402

from gongwen.core.classify import classify  # noqa: E402
from gongwen.core.reader import read_docx  # noqa: E402

html = root / "gongwen-web" / "dist" / "公文排版.html"
assert html.is_file(), "先运行 python gongwen-web/build.py"
tmp = Path(tempfile.mkdtemp())
src_docx = tmp / "通知 样例.docx"
d = docx.Document()
for line in NOTICE.splitlines():
    d.add_paragraph(line)
d.save(src_docx)
expected_types = [b.t for b in classify(read_docx(src_docx)).blocks]

exe = os.environ.get("PW_CHROMIUM") or ("/opt/pw-browsers/chromium" if Path("/opt/pw-browsers/chromium").exists() else None)
with sync_playwright() as p:
    b = p.chromium.launch(executable_path=exe) if exe else p.chromium.launch()
    ctx = b.new_context(viewport={"width": 1200, "height": 760}, accept_downloads=True)
    pg = ctx.new_page()
    errors, net = [], []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.on("request", lambda r: net.append(r.url) if not r.url.startswith(("file:", "data:", "blob:")) else None)
    pg.goto(html.as_uri())
    pg.wait_for_timeout(200)

    assert "打开一份 Word，或粘贴文字开始" in pg.inner_text("#empty")
    assert pg.is_disabled("#export")

    # 上传 .docx
    pg.set_input_files("#file-input", str(src_docx))
    pg.wait_for_selector("#blocks .row")
    rows = pg.eval_on_selector_all("#blocks .row select", "els => els.map(e => e.value)")
    assert rows == [t for t in expected_types if t != "table"], rows
    assert pg.is_checked('input[name="kind"][value="notice"]')

    # 改类型 → 预览字体变化
    assert "黑体" in pg.evaluate("getComputedStyle(document.querySelectorAll('#page [data-i]')[4]).fontFamily")
    pg.select_option("#blocks .row:nth-child(5) select", "body")
    assert "仿宋_GB2312" in pg.evaluate("getComputedStyle(document.querySelectorAll('#page [data-i]')[4]).fontFamily")

    # 行内回车不换行
    pg.click("#blocks .row:nth-child(4) .text")
    pg.keyboard.press("End")
    pg.keyboard.press("Enter")
    pg.keyboard.type("续")
    t = pg.inner_text("#blocks .row:nth-child(4) .text")
    assert "\n" not in t and t.endswith("续"), repr(t)
    assert "续" in pg.inner_text("#page")

    # 删除、切换简报
    pg.click("#blocks .row:nth-child(4) .del")
    assert pg.locator("#blocks .row").count() == 11
    pg.check('input[name="kind"][value="brief"]')
    assert pg.evaluate("document.querySelector('#page .blank-after-title') !== null")
    pg.check('input[name="kind"][value="notice"]')

    # 预览末两段：落款、日期（转为阿拉伯数字）右对齐
    tail = pg.evaluate("[...document.querySelectorAll('#page p')].slice(-2).map(p => [p.textContent, getComputedStyle(p).textAlign])")
    assert tail == [["评估矫治中心", "right"], ["2026年8月24日", "right"]], tail

    # 导出（默认）
    with pg.expect_download() as dl:
        pg.click("#export")
    path = tmp / dl.value.suggested_filename
    dl.value.save_as(path)
    assert dl.value.suggested_filename == "关于组织学习临释罪犯再犯风险评估相关内容的通知.docx"
    out = docx.Document(str(path))
    from docx.oxml.ns import qn
    assert out.paragraphs[0].runs[0]._element.rPr.rFonts.get(qn("w:eastAsia")) == "方正小标宋简体"
    assert "已保存到下载文件夹" in pg.inner_text("#notice")

    # 导出（勾选替代）：结果与页面里 chooseSubstitutes(detectFonts()) 一致
    subs = pg.evaluate("GW.chooseSubstitutes(GW.detectFonts())")
    pg.check("#substitute")
    with pg.expect_download() as dl2:
        pg.click("#export")
    p2 = tmp / "sub.docx"
    dl2.value.save_as(p2)
    title_font = docx.Document(str(p2)).paragraphs[0].runs[0]._element.rPr.rFonts.get(qn("w:eastAsia"))
    assert title_font == subs.get("方正小标宋简体", "方正小标宋简体"), (title_font, subs)
    pg.uncheck("#substitute")

    # 自检
    pg.click("#selftest")
    pg.wait_for_selector("#selftest-modal .item")
    items = pg.eval_on_selector_all("#selftest-modal .item", "els => els.map(e => e.dataset.ok)")
    assert len(items) == 3 and items[0] == "true", items
    pg.click("#selftest-close")

    # 打开 .doc 报错
    bad = tmp / "旧.doc"
    bad.write_bytes(b"\xd0\xcf\x11\xe0")
    pg.set_input_files("#file-input", str(bad))
    pg.wait_for_timeout(200)
    assert "暂不支持老版 .doc 文件" in pg.inner_text("#notice")

    # 1500 段：识别 + 预览 < 3 秒
    big = "大文档标题\n" + "\n".join(f"第{i}段正文内容，用于测试性能。" for i in range(1500))
    pg.click("#paste")
    pg.fill("#paste-text", big)
    start = time.time()
    pg.click("#paste-ok")
    pg.wait_for_function("document.querySelectorAll('#blocks .row').length === 1501")
    elapsed = time.time() - start
    assert elapsed < 3, f"1500 段耗时 {elapsed:.1f}s"

    # 布局与截图（回到通知样例）
    pg.set_input_files("#file-input", str(src_docx))
    pg.wait_for_function("document.querySelectorAll('#blocks .row').length === 12")
    pg.set_viewport_size({"width": 960, "height": 600})
    pg.wait_for_timeout(100)
    sw = pg.evaluate("document.documentElement.scrollWidth")
    assert sw <= 960, f"horizontal scroll {sw}"
    pg.set_viewport_size({"width": 1200, "height": 760})
    pg.wait_for_timeout(100)
    pg.screenshot(path=str(root / "docs/screenshots/gongwen-web.png"))

    # 有未导出修改时离开 → beforeunload 提醒
    pg.select_option("#blocks .row:nth-child(5) select", "body")
    with pg.expect_event("dialog", timeout=5000) as dlg:
        pg.close(run_before_unload=True)
    assert dlg.value.type == "beforeunload"
    dlg.value.accept()

    assert not net, f"不应有网络请求：{net}"
    assert not errors, errors
    print("Web UI smoke OK")
    b.close()
