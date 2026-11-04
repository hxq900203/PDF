const test = require("node:test");
const assert = require("node:assert");
const GW = require("./load")();

const NOTICE = `关于组织学习临释罪犯再犯风险评估
相关内容的通知
狱属各监区：
为进一步规范评估工作，具体通知如下：
一、认真组织学习，准确掌握量表填写要求
（一）系统初评为一般危险等级的
1、《临释罪犯再犯风险评估报告》；
一是要认真学。各监区要组织民警逐条学习。
附件：
1.《罪犯再犯风险评估量表（成年男犯）》及填写说明
2、《评估报告模板》
评估矫治中心
二〇二六年八月二十四日`;
const BRIEF = "心理为钥，精准疏导解心结\n近日，某监区开展心理疏导活动。\n一、全员覆盖筑根基，多维教育润心田\n活动覆盖全体服刑人员。";
const types = (text) => GW.classify(GW.readText(text)).blocks.map((b) => b.t);
const pairs = (text) => GW.classify(GW.readText(text)).blocks.map((b) => [b.t, b.text]);

test("notice end to end", () => {
  const d = GW.classify(GW.readText(NOTICE));
  assert.strictEqual(d.kind, "notice");
  assert.deepStrictEqual(d.blocks.map((b) => b.t), ["title", "title", "addressee", "body", "h1", "h2", "h3", "body",
    "attachment", "attachment", "signer", "date"]);
  assert.strictEqual(d.blocks[8].text, "《罪犯再犯风险评估量表（成年男犯）》及填写说明");
  assert.strictEqual(d.blocks[9].text, "《评估报告模板》");
});
test("brief", () => {
  const d = GW.classify(GW.readText(BRIEF));
  assert.strictEqual(d.kind, "brief");
  assert.deepStrictEqual(d.blocks.map((b) => b.t), ["title", "body", "h1", "body"]);
});
test("long numbered is body", () => {
  const long = "一、" + "各监区要高度重视，".repeat(6) + "确保工作落实到位。";
  assert.deepStrictEqual(types("标题\n" + long), ["title", "body"]);
});
test("second line with period", () => assert.deepStrictEqual(types("标题\n这是第一句话。"), ["title", "body"]));
test("second line numbered", () => assert.deepStrictEqual(types("标题\n一、总体要求"), ["title", "h1"]));
test("inline attachment", () => assert.deepStrictEqual(pairs("标题\n正文。\n附件：《评估报告模板》").pop(), ["attachment", "《评估报告模板》"]));
test("attachment zone ends", () => assert.deepStrictEqual(types("标题\n正文。\n附件\n（1）《甲》\n特此通知。"), ["title", "body", "attachment", "body"]));
test("irregular numbering", () => assert.deepStrictEqual(types("标题\n　　一 、甲\n(一)乙\n（二)丙\n1．丁\n（1）戊"), ["title", "h1", "h2", "h2", "h3", "h3"]));
test("yishi is body", () => assert.deepStrictEqual(types("标题\n一是加强领导。"), ["title", "body"]));
test("table first and single line", () => {
  assert.deepStrictEqual(GW.classify([{ t: "table", rows: [["a"]] }, { t: "body", text: "标题" }]).blocks.map((b) => b.t), ["table", "title"]);
  assert.deepStrictEqual(types("只有一行"), ["title"]);
});
test("signer requires date", () => assert.deepStrictEqual(types("标题\n正文。\n评估矫治中心"), ["title", "body", "body"]));
test("arabic date and signer", () => assert.deepStrictEqual(types("标题\n正文。\n评估矫治中心\n2026年8月24日"), ["title", "body", "signer", "date"]));
test("addressee rules", () => {
  assert.strictEqual(types("标题\n各监区：")[1], "addressee");
  assert.notStrictEqual(types("标题\n具体通知如下：为做好工作。现通知：")[1], "addressee");
});
test("decimal not heading", () => assert.deepStrictEqual(types("标题\n1.5万人参加了活动。"), ["title", "body"]));
test("inline numbered attachment", () => assert.deepStrictEqual(pairs("标题\n正文。\n附件：1.《量表》\n2.《说明》").slice(-2), [["attachment", "《量表》"], ["attachment", "《说明》"]]));
test("single unnumbered attachment", () => {
  assert.deepStrictEqual(pairs("标题\n正文。\n附件：\n《量表》").pop(), ["attachment", "《量表》"]);
  assert.deepStrictEqual(pairs("标题\n正文。\n附件\n《量表》\n特此通知。").pop(), ["body", "特此通知。"]);
});
test("circle zero date", () => assert.deepStrictEqual(types("标题\n正文。\n评估矫治中心\n二○二六年八月二十四日"), ["title", "body", "signer", "date"]));
test("readText cleaning", () => {
  assert.deepStrictEqual(GW.readText("　　一、标题\r\n\r\n  正文。\t\n\r末行").map((b) => b.text), ["一、标题", "正文。", "末行"]);
  assert.deepStrictEqual(GW.readText("标题\x0b第二行\x0c正文\x07内容。\x00").map((b) => b.text), ["标题", "第二行", "正文内容。"]);
  assert.throws(() => GW.readText("  \n "), /没有读到任何文字/);
});
