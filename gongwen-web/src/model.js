var GW = GW || {};
(function (GW) {
  "use strict";
  GW.TYPES = ["title", "addressee", "h1", "h2", "h3", "body", "attachment", "signer", "date", "table"];
  GW.KINDS = ["notice", "brief"];

  function GWError(message) {
    var e = new Error(message);
    e.name = "GWError";
    Object.setPrototypeOf(e, GWError.prototype);
    return e;
  }
  GWError.prototype = Object.create(Error.prototype);
  GWError.prototype.constructor = GWError;
  GW.GWError = GWError;

  var INVALID = /[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]/g;
  GW.cleanText = function (s) { return String(s).replace(INVALID, ""); };

  // 校验并清理界面传来的文档（同 Python Document.from_dict）
  GW.validateDoc = function (d) {
    if (!d || GW.KINDS.indexOf(d.kind) < 0) throw new GWError("文种无效");
    var blocks = (d.blocks || []).map(function (b) {
      if (!b || GW.TYPES.indexOf(b.t) < 0) throw new GWError("段落类型无效");
      if (b.t === "table") {
        return { t: "table", rows: (b.rows || []).map(function (r) { return r.map(function (c) { return GW.cleanText(c); }); }) };
      }
      return { t: b.t, text: GW.cleanText(b.text === undefined ? "" : b.text) };
    });
    return { kind: d.kind, blocks: blocks };
  };
})(GW);
