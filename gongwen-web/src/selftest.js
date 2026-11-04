var GW = GW || {};
(function (GW) {
  "use strict";
  var SAMPLE = "关于开展自检的通知\n各部门：\n一、自检内容\n请按要求完成自检。\n办公室\n2026年8月24日";

  function generate() {
    var doc = GW.classify(GW.readText(SAMPLE));
    return GW.buildDocx(doc).then(function (bytes) {
      return Promise.all([GW.readDocx(bytes.buffer, "自检.docx"), JSZip.loadAsync(bytes)]);
    }).then(function (res) {
      var back = res[0].map(function (b) { return b.text; }).join("|");
      var expected = GW.readText(SAMPLE).map(function (b) { return b.text; }).join("|");
      return res[1].file("word/document.xml").async("string").then(function (xml) {
        var firstFont = (xml.match(/w:eastAsia="([^"]+)"/) || [])[1];
        var ok = back === expected && firstFont === "方正小标宋简体" &&
          xml.indexOf('w:lineRule="exact"') >= 0 && xml.indexOf('w:line="520"') >= 0;
        return { name: "生成与读回", ok: ok,
                 detail: ok ? "已生成测试 Word 并读回，文字、字体、行距正确" : "读回结果不一致（" + back + "）" };
      });
    }).catch(function (e) {
      return { name: "生成与读回", ok: false, detail: "出错：" + (e && e.message ? e.message : e) };
    });
  }

  function fontsItem() {
    var detect = GW.detectFonts(), subs = GW.chooseSubstitutes(detect);
    var lines = GW.REQUIRED_FONTS.map(function (f) {
      if (detect[f]) return f + "：已安装";
      return f + "：未找到，" + (subs[f] ? "预览将使用：" + subs[f] : "未找到相似字体，将使用浏览器默认字体");
    });
    var missing = GW.REQUIRED_FONTS.filter(function (f) { return !detect[f]; });
    if (missing.length) lines.push("导出的 Word 不受影响，换到装有该字体的电脑上打开即为正确格式；本机预览会用替代字体");
    return { name: "字体", ok: !missing.length, detail: lines.join("\n") };
  }

  GW.runSelftest = function () {
    return generate().then(function (first) {
      return [first, fontsItem(), { name: "浏览器信息", ok: true, detail: navigator.userAgent }];
    });
  };
})(GW);
