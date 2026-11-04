var GW = GW || {};
(function (GW) {
  "use strict";
  // 界面逻辑：由 gongwen/web/app.js 改写为纯浏览器版（读写都在本地完成）
  var $ = function (id) { return document.getElementById(id); };
  var LABELS = { title: "标题", addressee: "主送机关", h1: "一级标题", h2: "二级标题", h3: "三级标题",
                 body: "正文", attachment: "附件", signer: "落款", date: "日期" };
  var state = { doc: null, selected: null, dirty: false, busy: false };
  var detected = GW.detectFonts();
  var previewSubs = GW.chooseSubstitutes(detected);

  // 预览字体栈（缺字体时用相似字体显示）
  (function setFontVars() {
    var root = document.documentElement.style;
    root.setProperty("--xbs", GW.cssStack("方正小标宋简体"));
    root.setProperty("--fs", GW.cssStack("仿宋_GB2312"));
    root.setProperty("--kt", GW.cssStack("楷体_GB2312"));
    root.setProperty("--ht", GW.cssStack("黑体"));
  })();
  var titleBold = !!previewSubs["方正小标宋简体"] && GW.BOLD_COMPENSATE.indexOf(previewSubs["方正小标宋简体"]) >= 0;

  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text !== undefined) e.textContent = text;
    return e;
  }
  function notify(text, ok) {
    $("notice").hidden = false;
    $("notice").classList.toggle("ok", !!ok);
    $("notice-text").textContent = text;
  }
  function errorText(e) {
    if (e && e.name === "GWError") return e.message;
    return "操作失败：" + (e && e.name ? e.name : "未知错误");
  }
  function changed() { state.dirty = true; renderPreview(); }

  // ---- 载入 ----
  function setDoc(doc) {
    state.doc = doc;
    state.selected = null;
    state.dirty = true;
    $("notice").hidden = true;
    document.querySelector('input[name="kind"][value="' + doc.kind + '"]').checked = true;
    renderList();
    renderPreview();
  }
  function loadFile(file) {
    if (!file) return;
    var reader = new FileReader();
    reader.onload = function () {
      GW.readDocx(reader.result, file.name).then(function (blocks) { setDoc(GW.classify(blocks)); })
        .catch(function (e) { notify(errorText(e)); });
    };
    reader.onerror = function () { notify("文件已损坏或无法读取"); };
    reader.readAsArrayBuffer(file);
  }

  // ---- 左栏 ----
  function renderList() {
    var has = !!(state.doc && state.doc.blocks.length);
    $("empty").hidden = has;
    $("export").disabled = !has;
    var ol = $("blocks");
    ol.innerHTML = "";
    if (!state.doc) return;
    var frag = document.createDocumentFragment();
    state.doc.blocks.forEach(function (b, i) {
      var li = el("li", "row t-" + b.t + (i === state.selected ? " sel" : ""));
      li.dataset.i = i;
      if (b.t === "table") {
        var cols = Math.max.apply(null, b.rows.map(function (r) { return r.length; }));
        li.appendChild(el("span", "tag", "表格"));
        li.appendChild(el("span", "text", "表格（" + b.rows.length + " 行 × " + cols + " 列）"));
      } else {
        var sel = el("select");
        Object.keys(LABELS).forEach(function (k) {
          var o = el("option", "", LABELS[k]); o.value = k; o.selected = k === b.t; sel.appendChild(o);
        });
        sel.addEventListener("change", function () { b.t = sel.value; li.className = "row t-" + b.t + " sel"; changed(); });
        var tx = el("div", "text", b.text);
        tx.contentEditable = "plaintext-only";
        tx.addEventListener("input", function () { b.text = tx.textContent.replace(/\n/g, ""); changed(); });
        // 一行就是一段：回车不换行；粘贴多行时合并为一行
        tx.addEventListener("keydown", function (e) { if (e.key === "Enter") e.preventDefault(); });
        tx.addEventListener("paste", function (e) {
          e.preventDefault();
          var text = (e.clipboardData.getData("text/plain") || "").replace(/[\r\n\v\f]+/g, "");
          document.execCommand("insertText", false, text);
        });
        li.appendChild(sel);
        li.appendChild(tx);
      }
      var del = el("button", "del", "×");
      del.title = "删除这一段";
      del.addEventListener("click", function (e) {
        e.stopPropagation();
        state.doc.blocks.splice(i, 1);
        state.selected = null;
        renderList();
        changed();
      });
      li.appendChild(del);
      li.addEventListener("click", function () { select(i); });
      frag.appendChild(li);
    });
    ol.appendChild(frag);
  }

  function select(i) {
    state.selected = i;
    Array.prototype.forEach.call(document.querySelectorAll("#blocks .row"), function (r) {
      r.classList.toggle("sel", Number(r.dataset.i) === i);
    });
    Array.prototype.forEach.call(document.querySelectorAll("#page .hl"), function (e) { e.classList.remove("hl"); });
    var target = document.querySelector('#page [data-i="' + i + '"]');
    if (target) { target.classList.add("hl"); target.scrollIntoView({ block: "nearest" }); }
  }

  // ---- 右栏预览（与 build.js 输出顺序一致）----
  function renderPreview() {
    var page = $("page");
    page.innerHTML = "";
    if (!state.doc) { fit(); return; }
    var blocks = state.doc.blocks, frag = document.createDocumentFragment();
    function p(cls, text, i) {
      var e = el("p", cls, text);
      if (i !== undefined) e.dataset.i = i;
      frag.appendChild(e);
      return e;
    }
    blocks.forEach(function (b, i) { if (b.t === "title") p("title" + (titleBold ? " bold" : ""), b.text, i); });
    if (state.doc.kind === "brief") p("noindent blank-after-title", "");
    blocks.forEach(function (b, i) {
      if (["title", "attachment", "signer", "date"].indexOf(b.t) >= 0) return;
      if (b.t === "table") {
        var t = el("table");
        t.dataset.i = i;
        b.rows.forEach(function (r) {
          var tr = el("tr");
          r.forEach(function (c) { tr.appendChild(el("td", "", c)); });
          t.appendChild(tr);
        });
        frag.appendChild(t);
        p("noindent", "");
        return;
      }
      p(b.t === "h3" ? "body" : b.t, b.text, i);
    });
    var att = [], signoff = [];
    blocks.forEach(function (b, i) {
      if (b.t === "attachment") att.push([b, i]);
      if (b.t === "signer" || b.t === "date") signoff.push([b, i]);
    });
    if (att.length) {
      p("body", "附件");
      att.forEach(function (x, n) { p("body", (n + 1) + "、" + x[0].text, x[1]); });
    }
    if (signoff.length) {
      p("right", "");
      signoff.forEach(function (x) { p("right", x[0].t === "date" ? GW.normalizeDate(x[0].text) : x[0].text, x[1]); });
    }
    page.appendChild(frag);
    if (state.selected !== null) {
      var s = page.querySelector('[data-i="' + state.selected + '"]');
      if (s) s.classList.add("hl");
    }
    fit();
  }

  function fit() {
    var right = $("right"), scaler = $("scaler"), page = $("page");
    var scale = Math.min(1, (right.clientWidth - 32) / page.offsetWidth);
    scaler.style.transform = "scale(" + scale + ")";
    scaler.style.width = page.offsetWidth + "px";
    scaler.style.height = page.offsetHeight * scale + "px";
  }
  window.addEventListener("resize", fit);

  // ---- 导出 ----
  function download(bytes, name) {
    var blob = new Blob([bytes], { type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document" });
    var a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = name;
    document.body.appendChild(a);
    a.click();
    setTimeout(function () { URL.revokeObjectURL(a.href); a.remove(); }, 1000);
  }
  $("export").addEventListener("click", function () {
    if (!state.doc || state.busy) return;
    state.busy = true;
    $("export").disabled = true;
    var subs = $("substitute").checked ? GW.chooseSubstitutes(GW.detectFonts()) : {};
    var name = GW.defaultFilename(state.doc);
    GW.buildDocx(state.doc, { substitutes: subs }).then(function (bytes) {
      download(bytes, name);
      state.dirty = false;
      var used = Object.keys(subs).map(function (k) { return k + "→" + subs[k]; });
      notify("已保存到下载文件夹：" + name + (used.length ? "（已使用替代字体：" + used.join("，") + "）" : ""), true);
    }).catch(function (e) { notify(errorText(e)); }).then(function () {
      state.busy = false;
      $("export").disabled = !(state.doc && state.doc.blocks.length);
    });
  });

  // ---- 其他事件 ----
  $("open").addEventListener("click", function () { $("file-input").click(); });
  $("file-input").addEventListener("change", function () {
    var f = $("file-input").files[0];
    $("file-input").value = "";
    loadFile(f);
  });
  $("paste").addEventListener("click", function () { $("modal").hidden = false; $("paste-text").focus(); });
  $("paste-cancel").addEventListener("click", function () { $("modal").hidden = true; });
  $("paste-ok").addEventListener("click", function () {
    try {
      var doc = GW.classify(GW.readText($("paste-text").value));
      $("modal").hidden = true;
      $("paste-text").value = "";
      setDoc(doc);
    } catch (e) { notify(errorText(e)); }
  });
  Array.prototype.forEach.call(document.querySelectorAll('input[name="kind"]'), function (r) {
    r.addEventListener("change", function () { if (state.doc && r.checked) { state.doc.kind = r.value; changed(); } });
  });
  $("notice-close").addEventListener("click", function () { $("notice").hidden = true; });
  $("selftest").addEventListener("click", function () {
    var list = $("selftest-list");
    list.innerHTML = "<li>正在检查…</li>";
    $("selftest-modal").hidden = false;
    GW.runSelftest().then(function (items) {
      list.innerHTML = "";
      items.forEach(function (it) {
        var li = el("li", "item ok-" + it.ok);
        li.dataset.ok = String(it.ok);
        li.appendChild(el("b", "", (it.ok ? "✅ " : "❌ ") + it.name));
        li.appendChild(document.createTextNode(it.detail));
        list.appendChild(li);
      });
    });
  });
  $("selftest-close").addEventListener("click", function () { $("selftest-modal").hidden = true; });
  document.addEventListener("dragover", function (e) { e.preventDefault(); });
  document.addEventListener("drop", function (e) {
    e.preventDefault();
    if (e.dataTransfer && e.dataTransfer.files.length) loadFile(e.dataTransfer.files[0]);
  });
  window.addEventListener("beforeunload", function (e) {
    if (state.doc && state.doc.blocks.length && state.dirty) { e.preventDefault(); e.returnValue = ""; }
  });

  renderList();
  renderPreview();
})(GW);
