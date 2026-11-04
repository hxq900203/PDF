const test = require("node:test");
const assert = require("node:assert");
const GW = require("./load")();

test("constants", () => {
  assert.deepStrictEqual(GW.TYPES, ["title", "addressee", "h1", "h2", "h3", "body", "attachment", "signer", "date", "table"]);
  assert.deepStrictEqual(GW.KINDS, ["notice", "brief"]);
});
test("invalid kind", () => assert.throws(() => GW.validateDoc({ kind: "x", blocks: [] }), (e) => e.name === "GWError" && e.message === "文种无效"));
test("invalid type", () => assert.throws(() => GW.validateDoc({ kind: "brief", blocks: [{ t: "xx", text: "" }] }), /段落类型无效/));
test("cleanText", () => assert.strictEqual(GW.cleanText("标\x01题"), "标题"));
test("validateDoc cleans", () => {
  const d = GW.validateDoc({ kind: "brief", blocks: [{ t: "title", text: "标\x0b题" }, { t: "table", rows: [["a\x07"]] }] });
  assert.deepStrictEqual(d, { kind: "brief", blocks: [{ t: "title", text: "标题" }, { t: "table", rows: [["a"]] }] });
});
