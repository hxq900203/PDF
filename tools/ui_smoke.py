# 界面冒烟测试：python tools/ui_smoke.py <仓库根目录>（需 pip install playwright）
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

root = Path(sys.argv[1])
FAKE = """
window.__calls = [];
const fmt = p => ({pdf:'pdf',png:'image',jpg:'image',docx:'word',xlsx:'excel'})[p.split('.').pop().toLowerCase()] || null;
const LAB = {pdf:'PDF',word:'Word',excel:'Excel',image:'PNG 图片'};
const T = {pdf:['word','image','excel'], image:['pdf'], word:['pdf','image'], excel:['pdf','image']};
window.pywebview = { api: {
  describe: async ps => ps.map(p => ({path:p, name:p.split('/').pop(), format:fmt(p), label: fmt(p)?LAB[fmt(p)]:null})),
  get_targets: async ps => { let s=null; for (const p of ps){const t=T[fmt(p)]; s = s? s.filter(x=>t.includes(x)) : t.slice();}
     return ['pdf','word','image','excel'].filter(k => (s||[]).includes(k)).map(k=>({key:k,label:LAB[k]})); },
  pick_files: async () => [], pick_folder: async () => { window.__picks = (window.__picks||0)+1; return 'D:/输出' + window.__picks; },
  start: async (...a) => { window.__calls.push(a); }, open_folder: async () => {},
}};
"""
with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/opt/pw-browsers/chromium')
    pg = b.new_page(viewport={"width": 720, "height": 520})
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.add_init_script(FAKE)
    pg.goto((root / "app/web/index.html").as_uri())
    pg.evaluate("window.addFiles(['C:/a/报告.pdf','C:/a/图.png','C:/a/说明.txt'])")
    pg.wait_for_timeout(100)
    assert pg.locator("#files li").count() == 3
    assert pg.is_visible("#no-targets"), "mixed batch should show no common targets"
    assert "不支持的文件格式" in pg.inner_text("#files")
    pg.click("#files li:first-child .remove")
    pg.wait_for_timeout(100)
    assert pg.inner_text("#targets") == "PDF"
    pg.click("#targets button")
    assert pg.is_visible("#merge-row")
    pg.evaluate("window.addFiles(['C:/a/年度 报告.pdf'])"); pg.wait_for_timeout(100)
    pg.click("#files li:nth-child(1) .remove"); pg.wait_for_timeout(100)   # remove png
    pg.click("#files li:nth-child(1) .remove"); pg.wait_for_timeout(100)   # remove txt
    pg.click("#targets button:has-text('PNG 图片')")
    assert pg.is_visible("#dpi-row") and not pg.is_visible("#merge-row")
    pg.evaluate("window.addFiles(['C:/a/损坏.pdf'])"); pg.wait_for_timeout(100)
    pg.click("#start")
    calls = pg.evaluate("window.__calls")
    assert calls[0][1] == "image" and calls[0][3]["dpi"] == 200, calls
    assert pg.is_disabled("#start")
    pg.evaluate("""window.onBackendEvent({type:'status',index:0,state:'done',outputs:[]});
                   window.onBackendEvent({type:'status',index:1,state:'error',message:'PDF 已加密，无法转换'});
                   window.onBackendEvent({type:'finished',ok:1,failed:1,out_dir:'C:/a'});""")
    assert "完成 1 个，失败 1 个" in pg.inner_text("#summary")
    assert pg.is_visible("#open-out") and not pg.is_disabled("#start")
    # I-5: 再次转换只处理未完成的文件
    pg.evaluate("window.addFiles(['C:/a/新.pdf'])"); pg.wait_for_timeout(100)
    pg.click("#start")
    calls = pg.evaluate("window.__calls")
    assert calls[-1][0] == ["C:/a/损坏.pdf", "C:/a/新.pdf"], calls[-1]
    assert "完成" in pg.inner_text("#files li:nth-child(1)")
    pg.evaluate("window.onBackendEvent({type:'status',index:0,state:'error',message:'x'});"
                "window.onBackendEvent({type:'status',index:1,state:'done',outputs:[]});"
                "window.onBackendEvent({type:'finished',ok:1,failed:1,out_dir:'C:/a'})")
    assert "❌ x" in pg.inner_text("#files li:nth-child(2)") and "完成" in pg.inner_text("#files li:nth-child(3)")
    # M-4: 已选“指定文件夹”时再次点击可重新选择
    pg.click('input[name="out"][value="custom"]'); pg.wait_for_timeout(100)
    pg.click('input[name="out"][value="custom"]'); pg.wait_for_timeout(100)
    assert pg.inner_text("#out-path") == "D:/输出2", pg.inner_text("#out-path")
    sw = pg.evaluate("document.documentElement.scrollWidth")
    assert sw <= 720, f"horizontal scroll {sw}"
    pg.set_viewport_size({"width": 900, "height": 680})
    pg.screenshot(path=str(root / "docs/screenshots/ui.png"), full_page=True)
    assert not errors, errors
    print("UI smoke OK")
    b.close()
