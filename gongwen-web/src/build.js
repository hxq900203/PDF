var GW = GW || {};
(function (GW) {
  "use strict";
  // 对应 gongwen/core/build.py（参数取自用户 skill 的 gw_build.py）；XML 细节对照 Python 生成的文件
  var FS = "仿宋_GB2312", HT = "黑体", KT = "楷体_GB2312", XBS = "方正小标宋简体";
  var SAN = 32, ER = 44, SI = 28; // 半磅：三号 16pt、二号 22pt、四号 14pt
  var FONTS = { addressee: HT, h1: HT, h2: KT, h3: FS, body: FS };
  GW.REQUIRED_FONTS = [XBS, FS, KT, HT];
  // 缺字体时依次尝试的相似字体（设计文档 5A）
  GW.FALLBACKS = {
    "方正小标宋简体": ["方正小标宋_GBK", "华文中宋", "宋体", "Source Han Serif SC", "Noto Serif CJK SC"],
    "仿宋_GB2312": ["仿宋", "方正仿宋_GBK", "华文仿宋", "Source Han Serif SC", "Noto Serif CJK SC"],
    "楷体_GB2312": ["楷体", "方正楷体_GBK", "华文楷体", "Source Han Serif SC", "Noto Serif CJK SC"],
    "黑体": ["方正黑体_GBK", "Source Han Sans SC", "Noto Sans CJK SC"]
  };
  // 这些字体比方正小标宋细，替代标题时加粗
  GW.BOLD_COMPENSATE = ["宋体", "Source Han Serif SC", "Noto Serif CJK SC"];
  var TEXT_WIDTH = 8312; // A4 宽 11906 − 左右边距各 1797（twip）

  var NS = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" ' +
           'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"';
  var HEAD = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n';

  function esc(s) {
    return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }
  // 与 python-docx run.text 一致：\t 写成 <w:tab/>，首尾有空白时保留空格
  function runText(text) {
    return text.split("\t").map(function (part, i) {
      var t = part ? '<w:t' + (/^\s|\s$/.test(part) ? ' xml:space="preserve"' : "") + ">" + esc(part) + "</w:t>" : "";
      return (i ? "<w:tab/>" : "") + t;
    }).join("");
  }
  function run(text, font, sz, bold) {
    if (!text) return "";
    return '<w:r><w:rPr><w:rFonts w:ascii="' + esc(font) + '" w:hAnsi="' + esc(font) + '" w:eastAsia="' + esc(font) +
      '" w:cs="' + esc(font) + '" w:hint="eastAsia"/>' + (bold ? "<w:b/>" : '<w:b w:val="0"/>') +
      '<w:sz w:val="' + sz + '"/></w:rPr>' + runText(text) + "</w:r>";
  }
  function para(text, font, sz, align, indent, bold) {
    return '<w:p><w:pPr><w:spacing w:lineRule="exact" w:line="520" w:before="0" w:after="160"/>' +
      (indent ? '<w:ind w:firstLine="640" w:firstLineChars="200"/>' : "") +
      '<w:jc w:val="' + align + '"/></w:pPr>' + run(text, font, sz, bold) + "</w:p>";
  }
  function table(rows, font) {
    var cols = Math.max.apply(null, rows.map(function (r) { return r.length; }));
    var w = Math.floor(TEXT_WIDTH / cols);
    var grid = "";
    for (var c = 0; c < cols; c++) grid += '<w:gridCol w:w="' + w + '"/>';
    var body = rows.map(function (row, i) {
      var cells = "";
      for (var j = 0; j < cols; j++) {
        var val = row[j] === undefined ? "" : row[j];
        cells += '<w:tc><w:tcPr><w:tcW w:type="dxa" w:w="' + w + '"/><w:vAlign w:val="center"/></w:tcPr>' +
          '<w:p><w:pPr><w:spacing w:after="0" w:line="240" w:lineRule="auto"/><w:jc w:val="center"/></w:pPr>' +
          run(String(val), i === 0 ? font(HT) : font(FS), SI, false) + "</w:p></w:tc>";
      }
      return "<w:tr>" + cells + "</w:tr>";
    }).join("");
    return '<w:tbl><w:tblPr><w:tblStyle w:val="TableGrid"/><w:tblW w:type="auto" w:w="0"/><w:jc w:val="center"/>' +
      '<w:tblLook w:firstColumn="1" w:firstRow="1" w:lastColumn="0" w:lastRow="0" w:noHBand="0" w:noVBand="1" w:val="04A0"/>' +
      "</w:tblPr><w:tblGrid>" + grid + "</w:tblGrid>" + body + "</w:tbl>";
  }

  function documentXml(doc, subs) {
    var font = function (name) { return subs[name] || name; };
    // 方正小标宋缺失、换成偏细的宋体类字体时，标题加粗以接近原效果
    var titleBold = !!subs[XBS] && GW.BOLD_COMPENSATE.indexOf(subs[XBS]) >= 0;
    var out = [];
    doc.blocks.forEach(function (b) { if (b.t === "title") out.push(para(b.text, font(XBS), ER, "center", false, titleBold)); });
    if (doc.kind === "brief") out.push(para("", FS, SAN, "center", false));
    doc.blocks.forEach(function (b) {
      if (["title", "attachment", "signer", "date"].indexOf(b.t) >= 0) return;
      if (b.t === "table") {
        if (b.rows && b.rows.length) { out.push(table(b.rows, font)); out.push(para("", FS, SAN, "both", false)); }
        return;
      }
      out.push(para(b.text, font(FONTS[b.t]), SAN, "both", b.t !== "addressee"));
    });
    var att = doc.blocks.filter(function (b) { return b.t === "attachment"; });
    if (att.length) {
      out.push(para("附件", font(FS), SAN, "both", true));
      att.forEach(function (b, i) { out.push(para((i + 1) + "、" + b.text, font(FS), SAN, "both", true)); });
    }
    var signoff = doc.blocks.filter(function (b) { return b.t === "signer" || b.t === "date"; });
    if (signoff.length) {
      out.push(para("", FS, SAN, "right", false));
      signoff.forEach(function (b) {
        out.push(para(b.t === "date" ? GW.normalizeDate(b.text) : b.text, font(FS), SAN, "right", false));
      });
    }
    var sect = '<w:sectPr><w:footerReference w:type="default" r:id="rId4"/><w:pgSz w:w="11906" w:h="16838"/>' +
      '<w:pgMar w:top="1440" w:right="1797" w:bottom="1440" w:left="1797" w:header="850" w:footer="992" w:gutter="0"/>' +
      '<w:cols w:space="720"/><w:docGrid w:linePitch="312" w:type="lines"/></w:sectPr>';
    return HEAD + "<w:document " + NS + "><w:body>" + out.join("") + sect + "</w:body></w:document>";
  }

  var STYLES = HEAD + "<w:styles " + NS + "><w:docDefaults><w:rPrDefault><w:rPr>" +
    '<w:rFonts w:ascii="' + FS + '" w:hAnsi="' + FS + '" w:eastAsia="' + FS + '" w:cs="' + FS + '"/>' +
    '<w:sz w:val="22"/><w:szCs w:val="22"/><w:kern w:val="2"/><w:lang w:val="en-US" w:eastAsia="zh-CN" w:bidi="ar-SA"/>' +
    '</w:rPr></w:rPrDefault><w:pPrDefault><w:pPr><w:spacing w:after="200" w:line="276" w:lineRule="auto"/></w:pPr></w:pPrDefault></w:docDefaults>' +
    '<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/><w:qFormat/><w:rPr>' +
    '<w:rFonts w:ascii="' + FS + '" w:hAnsi="' + FS + '" w:eastAsia="' + FS + '" w:cs="' + FS + '"/><w:sz w:val="32"/></w:rPr></w:style>' +
    '<w:style w:type="table" w:default="1" w:styleId="TableNormal"><w:name w:val="Normal Table"/><w:uiPriority w:val="99"/><w:semiHidden/><w:unhideWhenUsed/>' +
    '<w:tblPr><w:tblInd w:w="0" w:type="dxa"/><w:tblCellMar><w:top w:w="0" w:type="dxa"/><w:left w:w="108" w:type="dxa"/><w:bottom w:w="0" w:type="dxa"/><w:right w:w="108" w:type="dxa"/></w:tblCellMar></w:tblPr></w:style>' +
    '<w:style w:type="table" w:styleId="TableGrid"><w:name w:val="Table Grid"/><w:basedOn w:val="TableNormal"/><w:uiPriority w:val="59"/>' +
    '<w:pPr><w:spacing w:after="0" w:line="240" w:lineRule="auto"/></w:pPr><w:tblPr><w:tblInd w:w="0" w:type="dxa"/><w:tblBorders>' +
    ["top", "left", "bottom", "right", "insideH", "insideV"].map(function (s) {
      return "<w:" + s + ' w:val="single" w:sz="4" w:space="0" w:color="auto"/>';
    }).join("") +
    '</w:tblBorders><w:tblCellMar><w:top w:w="0" w:type="dxa"/><w:left w:w="108" w:type="dxa"/><w:bottom w:w="0" w:type="dxa"/><w:right w:w="108" w:type="dxa"/></w:tblCellMar></w:tblPr></w:style>' +
    "</w:styles>";

  var SETTINGS = HEAD + "<w:settings " + NS + '><w:defaultTabStop w:val="420"/><w:characterSpacingControl w:val="compressPunctuation"/>' +
    "<w:compat><w:spaceForUL/><w:balanceSingleByteDoubleByteWidth/><w:doNotLeaveBackslashAlone/><w:ulTrailSpace/>" +
    "<w:doNotExpandShiftReturn/><w:adjustLineHeightInTable/><w:useFELayout/>" +
    '<w:compatSetting w:name="compatibilityMode" w:uri="http://schemas.microsoft.com/office/word" w:val="15"/>' +
    '<w:compatSetting w:name="overrideTableStyleFontSizeAndJustification" w:uri="http://schemas.microsoft.com/office/word" w:val="1"/>' +
    '<w:compatSetting w:name="enableOpenTypeFeatures" w:uri="http://schemas.microsoft.com/office/word" w:val="1"/>' +
    '<w:compatSetting w:name="doNotFlipMirrorIndents" w:uri="http://schemas.microsoft.com/office/word" w:val="1"/>' +
    "</w:compat></w:settings>";

  function fontTable() {
    var family = { "方正小标宋简体": "roman", "仿宋_GB2312": "roman", "楷体_GB2312": "roman", "黑体": "swiss" };
    return HEAD + "<w:fonts " + NS + ">" + GW.REQUIRED_FONTS.map(function (f) {
      var alt = GW.FALLBACKS[f][0];
      return '<w:font w:name="' + f + '"><w:altName w:val="' + esc(alt) + '"/><w:charset w:val="86"/>' +
        '<w:family w:val="' + family[f] + '"/><w:pitch w:val="variable"/></w:font>';
    }).join("") + "</w:fonts>";
  }

  var FOOTER = HEAD + "<w:ftr " + NS + '><w:p><w:pPr><w:jc w:val="center"/></w:pPr>' +
    ['<w:fldChar w:fldCharType="begin"/>', '<w:instrText xml:space="preserve">PAGE   \\* MERGEFORMAT</w:instrText>',
     '<w:fldChar w:fldCharType="separate"/>', "<w:t>1</w:t>", '<w:fldChar w:fldCharType="end"/>'].map(function (x) {
      return '<w:r><w:rPr><w:sz w:val="18"/></w:rPr>' + x + "</w:r>";
    }).join("") + "</w:p></w:ftr>";

  var CT = HEAD + '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">' +
    '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>' +
    '<Default Extension="xml" ContentType="application/xml"/>' +
    '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>' +
    '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>' +
    '<Override PartName="/word/settings.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.settings+xml"/>' +
    '<Override PartName="/word/fontTable.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.fontTable+xml"/>' +
    '<Override PartName="/word/footer1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/>' +
    '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>' +
    '<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>' +
    "</Types>";
  var R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/";
  var RELS = HEAD + '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">' +
    '<Relationship Id="rId1" Type="' + R + 'officeDocument" Target="word/document.xml"/>' +
    '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>' +
    '<Relationship Id="rId3" Type="' + R + 'extended-properties" Target="docProps/app.xml"/></Relationships>';
  var DOC_RELS = HEAD + '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">' +
    '<Relationship Id="rId1" Type="' + R + 'styles" Target="styles.xml"/>' +
    '<Relationship Id="rId2" Type="' + R + 'settings" Target="settings.xml"/>' +
    '<Relationship Id="rId3" Type="' + R + 'fontTable" Target="fontTable.xml"/>' +
    '<Relationship Id="rId4" Type="' + R + 'footer" Target="footer1.xml"/></Relationships>';
  var CORE = HEAD + '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" ' +
    'xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:creator>公文排版</dc:creator></cp:coreProperties>';
  var APP = HEAD + '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"><Application>公文排版</Application></Properties>';

  // 返回 Promise<Uint8Array>；opts.substitutes：{规定字体: 替代字体}，见 fonts.js
  GW.buildDocx = function (doc, opts) {
    try {
      doc = GW.validateDoc(doc);
    } catch (e) {
      return Promise.reject(e);
    }
    var subs = (opts && opts.substitutes) || {};
    var zip = new JSZip();
    zip.file("[Content_Types].xml", CT);
    zip.file("_rels/.rels", RELS);
    zip.file("word/document.xml", documentXml(doc, subs));
    zip.file("word/styles.xml", STYLES);
    zip.file("word/settings.xml", SETTINGS);
    zip.file("word/fontTable.xml", fontTable());
    zip.file("word/footer1.xml", FOOTER);
    zip.file("word/_rels/document.xml.rels", DOC_RELS);
    zip.file("docProps/core.xml", CORE);
    zip.file("docProps/app.xml", APP);
    return zip.generateAsync({ type: "uint8array", compression: "DEFLATE" });
  };

  GW.defaultFilename = function (doc) {
    var title = doc.blocks.filter(function (b) { return b.t === "title"; }).map(function (b) { return b.text; }).join("");
    title = title.replace(/[\\/:*?"<>|\x00-\x1f\x7f]/g, "").trim();
    title = Array.from(title).slice(0, 80).join("").replace(/[. ]+$/, "");
    return (title || "公文") + ".docx";
  };
})(GW);
