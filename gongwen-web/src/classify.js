var GW = GW || {};
(function (GW) {
  "use strict";
  // 规则逐条对应 gongwen/core/classify.py 与 reader.py 的 _clean_lines
  var SHORT = 30, TITLE_MAX = 40, SIGNER_MAX = 20, H_MAX = 50;
  var D = "[0-9０-９]"; // Python 的 \d 也匹配全角数字
  var CN = "一二三四五六七八九十";
  var H1 = new RegExp("^[" + CN + "]+\\s*、");
  var H2 = new RegExp("^[（(][" + CN + "]+[）)]");
  var H3 = new RegExp("^(?:" + D + "+\\s*[、．]|" + D + "+\\.(?!" + D + ")|[（(]" + D + "+[）)])\\s*");
  var DATE = new RegExp("^(?:" + D + "{4}年" + D + "{1,2}月" + D + "{1,2}日|[〇○Ｏ０零一二三四五六七八九]{4}年[一二三四五六七八九十]{1,3}月[一二三四五六七八九十]{1,3}日)$");
  var ATTACH_HEAD = ["附件", "附件：", "附件:"];
  var ATTACH_INLINE = /^附件[：:]\s*([\s\S]+)$/;
  var NO_END = "。；，：:！？";
  var BREAKS = /\r\n|[\r\n\v\f\x85\u2028\u2029]/;
  var SPACES = " \t　 ";

  function strip(s) {
    var a = 0, b = s.length;
    while (a < b && SPACES.indexOf(s[a]) >= 0) a++;
    while (b > a && SPACES.indexOf(s[b - 1]) >= 0) b--;
    return s.slice(a, b);
  }
  GW._cleanLines = function (text) {
    return String(text).split(BREAKS).map(function (l) { return strip(GW.cleanText(l)); })
      .filter(function (l) { return l.length > 0; });
  };
  GW.readText = function (text) {
    var blocks = GW._cleanLines(text || "").map(function (l) { return { t: "body", text: l }; });
    if (!blocks.length) throw new GW.GWError("没有读到任何文字");
    return blocks;
  };

  function endsWithAny(t, chars) { return t.length > 0 && chars.indexOf(t[t.length - 1]) >= 0; }
  function numbered(t) { return H1.test(t) || H2.test(t) || H3.test(t); }
  function isHead(t) { return ATTACH_HEAD.indexOf(t) >= 0; }
  function heading(t) {
    var level = H1.test(t) ? "h1" : H2.test(t) ? "h2" : H3.test(t) ? "h3" : null;
    if (level === null || (len(t) > H_MAX && t[t.length - 1] === "。")) return "body";
    return level;
  }
  function len(t) { return Array.from(t).length; } // 与 Python 一样按字符计数
  function stripNum(t) { return t.replace(H3, ""); }

  GW.classify = function (input) {
    var blocks = input.map(function (b) { return b.t === "table" ? { t: "table", rows: b.rows } : { t: b.t, text: b.text }; });
    var n = blocks.length;
    var labels = blocks.map(function (b) { return b.t === "table" ? "table" : null; });
    var textIdx = [];
    for (var i = 0; i < n; i++) if (labels[i] === null) textIdx.push(i);
    if (!textIdx.length) return { kind: "brief", blocks: blocks };

    var first = textIdx[0];
    labels[first] = "title";
    var lastTitle = first, t;
    var nxt = first + 1;
    if (nxt < n && labels[nxt] === null) {
      t = blocks[nxt].text;
      if (len(t) <= TITLE_MAX && !endsWithAny(t, NO_END) && !numbered(t) && !DATE.test(t)) {
        labels[nxt] = "title";
        lastTitle = nxt;
      }
    }
    var k = lastTitle + 1;
    if (k < n && labels[k] === null) {
      t = blocks[k].text;
      if ((t[t.length - 1] === "：" || t[t.length - 1] === ":") && len(t) <= SHORT && t.indexOf("。") < 0 && !isHead(t)) {
        labels[k] = "addressee";
      }
    }
    var last = textIdx[textIdx.length - 1];
    if (labels[last] === null && DATE.test(blocks[last].text)) {
      labels[last] = "date";
      var s = last - 1;
      if (s >= 0 && labels[s] === null) {
        t = blocks[s].text;
        if (len(t) <= SIGNER_MAX && !endsWithAny(t, NO_END) && !numbered(t) && !isHead(t)) labels[s] = "signer";
      }
    }

    var out = [], inAttach = false, attachItems = 0, m;
    for (i = 0; i < n; i++) {
      var b = blocks[i];
      if (labels[i] === null) {
        t = b.text;
        if (isHead(t)) { inAttach = true; attachItems = 0; continue; }
        m = ATTACH_INLINE.exec(t);
        if (m) {
          inAttach = H3.test(m[1]);
          attachItems = 1;
          out.push({ t: "attachment", text: stripNum(m[1]) });
          continue;
        }
        if (inAttach && H3.test(t)) { attachItems++; out.push({ t: "attachment", text: stripNum(t) }); continue; }
        if (inAttach && attachItems === 0 && !numbered(t)) { inAttach = false; out.push({ t: "attachment", text: t }); continue; }
        inAttach = false;
        labels[i] = heading(t);
      } else if (labels[i] !== "table") {
        inAttach = false;
      }
      out.push(labels[i] === "table" ? { t: "table", rows: b.rows } : { t: labels[i], text: b.text });
    }
    var kind = out.some(function (x) { return x.t === "addressee"; }) ? "notice" : "brief";
    return { kind: kind, blocks: out };
  };
})(GW);
