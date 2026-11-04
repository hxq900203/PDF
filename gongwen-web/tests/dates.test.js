const test = require("node:test");
const assert = require("node:assert");
const GW = require("./load")();

const CASES = [
  ["二〇二六年八月二十四日", "2026年8月24日"],
  ["二〇二六年十月一日", "2026年10月1日"],
  ["二零二六年十二月三十一日", "2026年12月31日"],
  ["2026年8月24日", "2026年8月24日"],
  ["二〇二六年十三月一日", "二〇二六年十三月一日"],
  ["二〇二六年二月三十二日", "二〇二六年二月三十二日"],
  ["八月", "八月"],
  ["二○二六年八月二十四日", "2026年8月24日"],
  ["二Ｏ二六年八月二十四日", "2026年8月24日"],
];
for (const [src, dst] of CASES) {
  test(`normalizeDate ${src}`, () => assert.strictEqual(GW.normalizeDate(src), dst));
}
