const test = require("node:test");
const assert = require("node:assert");
const GW = require("./load")();

const ALL = [].concat(GW.REQUIRED_FONTS, ...Object.values(GW.FALLBACKS));
const detect = (present) => Object.fromEntries(ALL.map((f) => [f, present.includes(f)]));

test("chooseSubstitutes picks first installed fallback for missing fonts", () => {
  const d = detect(["宋体", "仿宋_GB2312", "楷体", "黑体"]);
  assert.deepStrictEqual(GW.chooseSubstitutes(d), { "方正小标宋简体": "宋体", "楷体_GB2312": "楷体" });
});
test("all installed → no substitutes", () => assert.deepStrictEqual(GW.chooseSubstitutes(detect(ALL)), {}));
test("nothing installed → no substitutes", () => assert.deepStrictEqual(GW.chooseSubstitutes(detect([])), {}));
test("cssStack", () => {
  assert.strictEqual(GW.cssStack("黑体"), '"黑体", "方正黑体_GBK", "Source Han Sans SC", "Noto Sans CJK SC", sans-serif');
  assert.ok(GW.cssStack("仿宋_GB2312").startsWith('"仿宋_GB2312", "仿宋"') && GW.cssStack("仿宋_GB2312").endsWith("serif"));
});
