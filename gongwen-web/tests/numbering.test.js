const test = require("node:test");
const assert = require("node:assert");
const GW = require("./load")();

test("formatNumber", () => {
  const f = GW.formatNumber;
  assert.deepStrictEqual([1, 10, 11, 20, 24].map((n) => f(n, "chineseCounting")), ["一", "十", "十一", "二十", "二十四"]);
  assert.strictEqual(f(3, "decimalEnclosedCircle"), "③");
  assert.strictEqual(f(28, "upperLetter"), "AB");
  assert.strictEqual(f(2, "lowerLetter"), "b");
  assert.strictEqual(f(12, "decimalFullWidth"), "１２");
  assert.strictEqual(f(5, "bullet"), "");
  assert.strictEqual(f(7, "somethingElse"), "7");
});
