var GW = GW || {};
(function (GW) {
  "use strict";
  // 缺字体替代（设计文档 5A）。FALLBACKS、BOLD_COMPENSATE 定义在 build.js。
  GW.ALL_FONTS = function () {
    var all = GW.REQUIRED_FONTS.slice();
    GW.REQUIRED_FONTS.forEach(function (f) { all = all.concat(GW.FALLBACKS[f]); });
    return all.filter(function (f, i) { return all.indexOf(f) === i; });
  };

  // detect: {字体名: 是否已安装} → {缺失的规定字体: 第一个已安装的替代字体}
  GW.chooseSubstitutes = function (detect) {
    var subs = {};
    GW.REQUIRED_FONTS.forEach(function (f) {
      if (detect[f]) return;
      var alt = GW.FALLBACKS[f].filter(function (x) { return detect[x]; })[0];
      if (alt) subs[f] = alt;
    });
    return subs;
  };

  GW.cssStack = function (required) {
    var generic = required === "黑体" ? "sans-serif" : "serif";
    return [required].concat(GW.FALLBACKS[required]).map(function (f) { return '"' + f + '"'; }).join(", ") + ", " + generic;
  };

  // 浏览器里判断字体是否已安装：与通用字体比较同一段文字的宽度
  var SAMPLE = "测试文字永和ABCabc123";
  GW.detectFonts = function () {
    var ctx = document.createElement("canvas").getContext("2d");
    function width(family) { ctx.font = "32px " + family; return ctx.measureText(SAMPLE).width; }
    var base = { monospace: width("monospace"), serif: width("serif"), "sans-serif": width("sans-serif") };
    var result = {};
    GW.ALL_FONTS().forEach(function (f) {
      result[f] = Object.keys(base).some(function (g) { return width('"' + f + '", ' + g) !== base[g]; });
    });
    return result;
  };
})(GW);
