var GW = GW || {};
(function (GW) {
  "use strict";
  // 对应 gongwen/core/reader.py
  var W = GW.W_NS, kids = GW._kids, kid = GW._kid, attr = GW._attr;
  var MC = "http://schemas.openxmlformats.org/markup-compatibility/2006";

  function skipped(el, stop) {
    for (var e = el; e && e !== stop; e = e.parentNode) {
      if (e.namespaceURI === W && (e.localName === "del" || e.localName === "txbxContent")) return true;
      if (e.namespaceURI === MC && e.localName === "Fallback") return true;
    }
    return false;
  }

  // 段落全部可见文字：w:t、w:tab→\t、w:br/w:cr→\n；跳过删除的修订、文本框、兼容回退
  function paraText(p) {
    var parts = [];
    (function walk(node) {
      for (var c = node.firstChild; c; c = c.nextSibling) {
        if (c.nodeType !== 1) continue;
        if (c.namespaceURI === W) {
          if (c.localName === "t") { if (!skipped(c, p)) parts.push(c.textContent || ""); continue; }
          if (c.localName === "tab") { if (!skipped(c, p)) parts.push("\t"); continue; }
          if (c.localName === "br" || c.localName === "cr") { if (!skipped(c, p)) parts.push("\n"); continue; }
        }
        walk(c);
      }
    })(p);
    return parts.join("");
  }

  function cellText(tc) {
    var ps = tc.getElementsByTagNameNS(W, "p"), texts = [];
    for (var i = 0; i < ps.length; i++) texts.push(paraText(ps[i]));
    return GW._cleanLines(texts.join("\n")).join("\n");
  }

  // 与 python-docx row.cells 一致：横向合并按跨列数重复，纵向合并的后续格取上方格的文字
  function tableRows(tbl) {
    var rows = [], above = [];
    kids(tbl, "tr").forEach(function (tr) {
      var row = [], col = 0;
      kids(tr, "tc").forEach(function (tc) {
        var pr = kid(tc, "tcPr");
        var spanEl = kid(pr, "gridSpan");
        var span = spanEl ? parseInt(attr(spanEl, "val"), 10) || 1 : 1;
        var vm = kid(pr, "vMerge");
        var cont = vm && attr(vm, "val") !== "restart";
        var text = cont && above[col] !== undefined ? above[col] : cellText(tc);
        for (var s = 0; s < span; s++) { row.push(text); col++; }
      });
      above = row.slice();
      rows.push(row);
    });
    return rows;
  }

  function walk(parent, numbering, blocks) {
    for (var el = parent.firstChild; el; el = el.nextSibling) {
      if (el.nodeType !== 1 || el.namespaceURI !== W) continue;
      if (el.localName === "p") {
        GW._cleanLines(numbering.prefix(el) + paraText(el)).forEach(function (l) { blocks.push({ t: "body", text: l }); });
      } else if (el.localName === "tbl") {
        var rows = tableRows(el);
        if (rows.some(function (r) { return r.some(function (c) { return c; }); })) blocks.push({ t: "table", rows: rows });
      } else if (el.localName === "sdt") {
        var content = kid(el, "sdtContent");
        if (content) walk(content, numbering, blocks);
      } else if (el.localName === "customXml") {
        walk(el, numbering, blocks);
      }
    }
  }

  function parse(xml) { return xml ? new DOMParser().parseFromString(xml, "application/xml") : null; }

  GW.readDocx = function (arrayBuffer, filename) {
    if (/\.doc$/i.test(filename || "")) {
      return Promise.reject(new GW.GWError("暂不支持老版 .doc 文件，请先用「文件转换器」转为 .docx，或复制文字后点「粘贴文字」"));
    }
    var broken = function () { throw new GW.GWError("文件已损坏或无法读取"); };
    return JSZip.loadAsync(arrayBuffer).then(function (zip) {
      var file = function (name) { var f = zip.file(name); return f ? f.async("string") : Promise.resolve(null); };
      return Promise.all([file("word/document.xml"), file("word/numbering.xml"), file("word/styles.xml")]);
    }, broken).then(function (xmls) {
      if (!xmls[0]) broken();
      var doc = parse(xmls[0]);
      var body = kid(doc.documentElement, "body");
      if (!body) broken();
      var blocks = [];
      walk(body, new GW.Numbering(parse(xmls[1]), parse(xmls[2])), blocks);
      if (!blocks.length) throw new GW.GWError("没有读到任何文字");
      return blocks;
    });
  };
})(GW);
