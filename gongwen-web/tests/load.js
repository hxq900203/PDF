// 在 Node 中按浏览器方式加载核心脚本（普通脚本，挂在全局 GW 上），供测试使用。
const fs = require("fs");
const path = require("path");
const vm = require("vm");
const { DOMParser, XMLSerializer } = require("@xmldom/xmldom");

const ROOT = path.join(__dirname, "..");
const CORE = ["dates", "model", "classify", "numbering", "reader", "build", "fonts"];
let loaded = null;

module.exports = function load() {
  if (loaded) return loaded;
  globalThis.DOMParser = DOMParser;
  globalThis.XMLSerializer = XMLSerializer;
  vm.runInThisContext(fs.readFileSync(path.join(ROOT, "vendor", "jszip.min.js"), "utf8"), { filename: "jszip.min.js" });
  for (const name of CORE) {
    const file = path.join(ROOT, "src", name + ".js");
    if (fs.existsSync(file)) vm.runInThisContext(fs.readFileSync(file, "utf8"), { filename: file });
  }
  loaded = globalThis.GW;
  return loaded;
};
