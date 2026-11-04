# 公文排版界面冒烟测试：python tools/gongwen_ui_smoke.py <仓库根目录>（需 pip install playwright）
import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

root = Path(sys.argv[1])
sys.path[:0] = [str(root), str(root / "tests" / "gongwen")]
from samples import NOTICE  # noqa: E402

from gongwen.api import Api  # noqa: E402

DOC = Api().parse_text(NOTICE)["doc"]
FAKE = """
window.__exports = [];
window.pywebview = { api: {
  parse_text: async t => (t.trim() ? {doc: %s} : {error: "没有读到任何文字"}),
  open_docx: async p => ({error: "文件已损坏或无法读取"}),
  pick_docx: async () => null,
  export: async d => { window.__exports.push(d); return {path: "C:/a/通知.docx"}; },
  open_file: async () => {},
}};
""" % json.dumps(DOC, ensure_ascii=False)


def preview_font(pg, i):
    return pg.evaluate(f"getComputedStyle(document.querySelectorAll('#page [data-i]')[{i}]).fontFamily")


with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/opt/pw-browsers/chromium")
    pg = b.new_page(viewport={"width": 1200, "height": 760})
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.add_init_script(FAKE)
    pg.goto((root / "gongwen/web/index.html").as_uri())
    pg.wait_for_timeout(100)

    assert pg.is_visible("#empty") and "打开一份 Word，或粘贴文字开始" in pg.inner_text("#empty")
    assert pg.is_disabled("#export")

    # 粘贴文字
    pg.click("#paste")
    pg.fill("#paste-text", "随便什么文字")
    pg.click("#paste-ok")
    pg.wait_for_timeout(150)
    assert pg.locator("#blocks .row").count() == 12
    assert "方正小标宋简体" in preview_font(pg, 0)
    assert pg.is_checked('input[name="kind"][value="notice"]')

    # 第 5 行（一级标题）改成正文 → 预览字体变仿宋
    assert "黑体" in preview_font(pg, 4)
    pg.select_option("#blocks .row:nth-child(5) select", "body")
    pg.wait_for_timeout(50)
    assert "仿宋_GB2312" in preview_font(pg, 4)

    # 预览末两段：落款、日期（已转阿拉伯数字），右对齐
    tail = pg.evaluate("""[...document.querySelectorAll('#page p')].slice(-2)
        .map(p => [p.textContent, getComputedStyle(p).textAlign])""")
    assert tail == [["评估矫治中心", "right"], ["2026年8月24日", "right"]], tail

    # 点击左侧行 → 预览高亮
    pg.click("#blocks .row:nth-child(3) .text")
    assert pg.locator("#page .hl").count() == 1 and pg.inner_text("#page .hl") == "狱属各监区："

    # 编辑文字 → 预览更新
    pg.click("#blocks .row:nth-child(4) .text")
    pg.keyboard.press("End")
    pg.keyboard.type("（已改）")
    pg.wait_for_timeout(50)
    assert "（已改）" in pg.inner_text("#page")

    # 在行内按回车不会产生预览里看不到的换行
    pg.click("#blocks .row:nth-child(4) .text")
    pg.keyboard.press("End")
    pg.keyboard.press("Enter")
    pg.keyboard.type("续")
    pg.wait_for_timeout(50)
    row_text = pg.inner_text("#blocks .row:nth-child(4) .text")
    assert "\n" not in row_text and row_text.endswith("（已改）续"), repr(row_text)

    # 删除一行
    pg.click("#blocks .row:nth-child(4) .del")
    pg.wait_for_timeout(50)
    assert pg.locator("#blocks .row").count() == 11

    # 切换信息简报 → 标题后出现空段
    pg.check('input[name="kind"][value="brief"]')
    pg.wait_for_timeout(50)
    assert pg.evaluate("document.querySelector('#page .blank-after-title') !== null")

    # 导出
    pg.click("#export")
    pg.wait_for_timeout(100)
    exported = pg.evaluate("window.__exports")[0]
    assert exported["kind"] == "brief" and len(exported["blocks"]) == 11
    assert exported["blocks"][3]["t"] == "body"  # 删掉第 4 行后，改过类型的那段前移到索引 3
    assert pg.is_visible("#notice-open") and "已导出" in pg.inner_text("#notice")

    # 打开文件出错时显示提示
    pg.evaluate("window.loadPath('C:/a/坏.docx')")
    pg.wait_for_timeout(100)
    assert "文件已损坏或无法读取" in pg.inner_text("#notice")

    pg.set_viewport_size({"width": 960, "height": 600})
    pg.wait_for_timeout(100)
    sw = pg.evaluate("document.documentElement.scrollWidth")
    assert sw <= 960, f"horizontal scroll {sw}"
    pg.set_viewport_size({"width": 1200, "height": 760})
    pg.wait_for_timeout(100)
    pg.screenshot(path=str(root / "docs/screenshots/gongwen.png"))
    assert not errors, errors
    print("UI smoke OK")
    b.close()
