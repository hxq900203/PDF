const test = require("node:test");
const assert = require("node:assert");
const GW = require("./load")();

const doc = (blocks) => ({ kind: "brief", blocks });
test("defaultFilename", () => {
  assert.strictEqual(GW.defaultFilename(doc([{ t: "title", text: "关于“A/B”的" }, { t: "title", text: "通知" }])), "关于“AB”的通知.docx");
  assert.strictEqual(GW.defaultFilename(doc([{ t: "body", text: "x" }])), "公文.docx");
  assert.strictEqual(GW.defaultFilename(doc([{ t: "title", text: '<>:"|?*' }])), "公文.docx");
  assert.strictEqual(GW.defaultFilename(doc([{ t: "title", text: "关于\t通知. " }])), "关于通知.docx");
  const name = GW.defaultFilename(doc([{ t: "title", text: "很长".repeat(100) }]));
  assert.ok(name.endsWith(".docx") && Array.from(name).length <= 85);
});
test("buildDocx rejects invalid doc", async () => {
  await assert.rejects(GW.buildDocx({ kind: "x", blocks: [] }), /文种无效/);
});
