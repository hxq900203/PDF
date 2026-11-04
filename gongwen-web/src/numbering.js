var GW = GW || {};
(function (GW) {
  "use strict";
  // 对应 gongwen/core/numbering.py：把 Word 自动编号还原成文字前缀
  var W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main";
  GW.W_NS = W;
  var CN = "零一二三四五六七八九";
  var CIRCLED = "①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳";
  var CHINESE_FMTS = ["chineseCounting", "chineseCountingThousand", "chineseLegalSimplified", "ideographTraditional",
                      "taiwaneseCounting", "taiwaneseCountingThousand"];

  function chinese(n) {
    if (n < 10) return CN[n];
    if (n < 100) {
      var tens = Math.floor(n / 10), ones = n % 10;
      return (tens === 1 ? "" : CN[tens]) + "十" + (ones ? CN[ones] : "");
    }
    return String(n);
  }
  function letters(n) {
    var s = "";
    while (n > 0) { var r = (n - 1) % 26; s = String.fromCharCode(97 + r) + s; n = Math.floor((n - 1) / 26); }
    return s;
  }
  GW.formatNumber = function (n, fmt) {
    if (CHINESE_FMTS.indexOf(fmt) >= 0) return chinese(n);
    if (fmt === "decimalEnclosedCircle" || fmt === "decimalEnclosedCircleChinese") {
      return n >= 1 && n <= 20 ? Array.from(CIRCLED)[n - 1] : String(n);
    }
    if (fmt === "decimalFullWidth" || fmt === "decimalFullWidth2") {
      return String(n).split("").map(function (c) { return String.fromCharCode(c.charCodeAt(0) + 0xFEE0); }).join("");
    }
    if (fmt === "lowerLetter") return letters(n);
    if (fmt === "upperLetter") return letters(n).toUpperCase();
    if (fmt === "bullet" || fmt === "none") return "";
    return String(n);
  };

  // ---- 小工具（DOM Level 2，兼容 xmldom）----
  function kids(el, name) {
    var out = [];
    if (!el) return out;
    for (var c = el.firstChild; c; c = c.nextSibling) {
      if (c.nodeType === 1 && c.namespaceURI === W && c.localName === name) out.push(c);
    }
    return out;
  }
  function kid(el, name) { var k = kids(el, name); return k.length ? k[0] : null; }
  function attr(el, name) { return el ? el.getAttributeNS(W, name) : null; }
  function val(el, name, dflt) {
    var k = kid(el, name);
    var v = k ? attr(k, "val") : null;
    return v === null || v === "" || v === undefined ? dflt : v;
  }
  GW._kids = kids; GW._kid = kid; GW._attr = attr;

  function Numbering(numberingDoc, stylesDoc) {
    this.nums = {}; this.abstract = {}; this.styles = {}; this.counters = {};
    var self = this;
    if (numberingDoc) {
      var root = numberingDoc.documentElement;
      kids(root, "abstractNum").forEach(function (a) { self.abstract[attr(a, "abstractNumId")] = a; });
      kids(root, "num").forEach(function (n) {
        var aid = kid(n, "abstractNumId");
        var starts = {};
        kids(n, "lvlOverride").forEach(function (ov) {
          var so = kid(ov, "startOverride");
          if (so) starts[attr(ov, "ilvl")] = parseInt(attr(so, "val"), 10);
        });
        if (aid) self.nums[attr(n, "numId")] = { aid: attr(aid, "val"), starts: starts };
      });
    }
    if (stylesDoc) kids(stylesDoc.documentElement, "style").forEach(function (s) { self.styles[attr(s, "styleId")] = s; });
  }

  Numbering.prototype.styleNumPr = function (styleId) {
    var seen = {};
    while (styleId && !seen[styleId]) {
      seen[styleId] = true;
      var style = this.styles[styleId];
      if (!style) return null;
      var numpr = kid(kid(style, "pPr"), "numPr");
      if (numpr) return numpr;
      var based = kid(style, "basedOn");
      styleId = based ? attr(based, "val") : null;
    }
    return null;
  };

  Numbering.prototype.prefix = function (p) {
    var ppr = kid(p, "pPr");
    var numpr = kid(ppr, "numPr");
    if (!numpr && ppr) {
      var ps = kid(ppr, "pStyle");
      numpr = ps ? this.styleNumPr(attr(ps, "val")) : null;
    }
    if (!numpr) return "";
    var nidEl = kid(numpr, "numId"), ilvlEl = kid(numpr, "ilvl");
    var numId = nidEl ? attr(nidEl, "val") : null;
    var ilvl = ilvlEl ? parseInt(attr(ilvlEl, "val"), 10) : 0;
    var num = this.nums[numId];
    if (!num) return "";
    var abstract = this.abstract[num.aid];
    if (!abstract) return "";
    var levels = {};
    kids(abstract, "lvl").forEach(function (l) { levels[parseInt(attr(l, "ilvl"), 10)] = l; });
    var lvl = levels[ilvl];
    if (!lvl) return "";
    var counters = this.counters[numId] || (this.counters[numId] = [null, null, null, null, null, null, null, null, null]);
    var start = (String(ilvl) in num.starts) ? num.starts[String(ilvl)] : parseInt(val(lvl, "start", "1"), 10);
    counters[ilvl] = counters[ilvl] === null ? start : counters[ilvl] + 1;
    for (var d = ilvl + 1; d < 9; d++) counters[d] = null;
    var text = val(lvl, "lvlText", "");
    for (var k = 0; k < 9; k++) {
      var token = "%" + (k + 1);
      if (text.indexOf(token) >= 0) {
        var l = levels[k];
        var n = counters[k] !== null ? counters[k] : (l ? parseInt(val(l, "start", "1"), 10) : 1);
        var fmt = l ? val(l, "numFmt", "decimal") : "decimal";
        text = text.split(token).join(GW.formatNumber(n, fmt));
      }
    }
    return text;
  };
  GW.Numbering = Numbering;
})(GW);
