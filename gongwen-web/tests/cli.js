// 测试用命令行：node cli.js read <docx> | classify <txt> | build <doc.json> <out.docx> [subs.json]
// 出错（GWError）时把中文消息写到 stderr，退出码 2。
const fs = require("fs");
const GW = require("./load")();

async function main() {
  const [cmd, a, b, c] = process.argv.slice(2);
  if (cmd === "classify") {
    process.stdout.write(JSON.stringify(GW.classify(GW.readText(fs.readFileSync(a, "utf8")))));
  } else if (cmd === "read") {
    const buf = fs.readFileSync(a);
    const blocks = await GW.readDocx(buf.buffer.slice(buf.byteOffset, buf.byteOffset + buf.byteLength), a);
    process.stdout.write(JSON.stringify(blocks));
  } else if (cmd === "build") {
    const doc = JSON.parse(fs.readFileSync(a, "utf8"));
    const subs = c ? JSON.parse(fs.readFileSync(c, "utf8")) : {};
    fs.writeFileSync(b, await GW.buildDocx(doc, { substitutes: subs }));
  } else {
    throw new Error("未知命令 " + cmd);
  }
}
main().catch((e) => {
  process.stderr.write(e.message);
  process.exit(e.name === "GWError" ? 2 : 1);
});
