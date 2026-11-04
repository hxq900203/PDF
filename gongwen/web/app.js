(() => {
  const $ = (id) => document.getElementById(id);
  const api = () => window.pywebview.api;
  const LABELS = { title: "标题", addressee: "主送机关", h1: "一级标题", h2: "二级标题", h3: "三级标题",
                   body: "正文", attachment: "附件", signer: "落款", date: "日期" };
  const state = { doc: null, selected: null, busy: false };

  // ---- 工具 ----
  const DIG = { "〇": 0, "零": 0, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9 };
  function small(s) {
    if (!s.includes("十")) return s.length === 1 && s in DIG ? DIG[s] : null;
    const [tens, ones] = s.split("十");
    if (tens.length > 1 || ones.length > 1 || (tens && !(tens in DIG)) || (ones && !(ones in DIG))) return null;
    return (tens ? DIG[tens] : 1) * 10 + (ones ? DIG[ones] : 0);
  }
  // 与 gongwen/core/dates.py 规则一致
  function normalizeDate(s) {
    const m = s.trim().match(/^([〇零一二三四五六七八九]{4})年([一二三四五六七八九十]{1,3})月([一二三四五六七八九十]{1,3})日$/);
    if (!m) return s;
    const y = [...m[1]].map((c) => DIG[c]).join(""), mo = small(m[2]), d = small(m[3]);
    if (mo === null || d === null || mo < 1 || mo > 12 || d < 1 || d > 31) return s;
    return `${y}年${mo}月${d}日`;
  }
  function el(tag, cls, text) {
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text !== undefined) e.textContent = text;
    return e;
  }

  // ---- 提示条 ----
  function notify(text, ok, path) {
    $("notice").hidden = false;
    $("notice").classList.toggle("ok", !!ok);
    $("notice-text").textContent = text;
    $("notice-open").hidden = !path;
    $("notice-open").dataset.path = path || "";
  }

  // ---- 载入 ----
  function setDoc(result) {
    if (result.error) { notify(result.error); return; }
    state.doc = result.doc;
    state.selected = null;
    $("notice").hidden = true;
    document.querySelector(`input[name="kind"][value="${state.doc.kind}"]`).checked = true;
    renderList();
    renderPreview();
  }
  window.loadPath = async (path) => setDoc(await api().open_docx(path));

  // ---- 左栏 ----
  function renderList() {
    const has = !!(state.doc && state.doc.blocks.length);
    $("empty").hidden = has;
    $("export").disabled = !has;
    const ol = $("blocks");
    ol.innerHTML = "";
    if (!state.doc) return;
    state.doc.blocks.forEach((b, i) => {
      const li = el("li", `row t-${b.t}` + (i === state.selected ? " sel" : ""));
      li.dataset.i = i;
      if (b.t === "table") {
        li.append(el("span", "tag", "表格"),
                  el("span", "text", `表格（${b.rows.length} 行 × ${Math.max(...b.rows.map((r) => r.length))} 列）`));
      } else {
        const sel = el("select");
        for (const [k, v] of Object.entries(LABELS)) {
          const o = el("option", "", v); o.value = k; o.selected = k === b.t; sel.append(o);
        }
        sel.addEventListener("change", () => { b.t = sel.value; li.className = `row t-${b.t} sel`; renderPreview(); });
        const tx = el("div", "text", b.text);
        tx.contentEditable = "plaintext-only";
        tx.addEventListener("input", () => { b.text = tx.textContent.replace(/\n/g, ""); renderPreview(); });
        li.append(sel, tx);
      }
      const del = el("button", "del", "×");
      del.title = "删除这一段";
      del.addEventListener("click", (e) => {
        e.stopPropagation();
        state.doc.blocks.splice(i, 1);
        state.selected = null;
        renderList(); renderPreview();
      });
      li.append(del);
      li.addEventListener("click", () => select(i));
      ol.append(li);
    });
  }

  function select(i) {
    state.selected = i;
    document.querySelectorAll("#blocks .row").forEach((r) => r.classList.toggle("sel", Number(r.dataset.i) === i));
    document.querySelectorAll("#page .hl").forEach((e) => e.classList.remove("hl"));
    const target = document.querySelector(`#page [data-i="${i}"]`);
    if (target) { target.classList.add("hl"); target.scrollIntoView({ block: "nearest" }); }
  }

  // ---- 右栏预览（与 gongwen/core/build.py 输出顺序一致）----
  function renderPreview() {
    const page = $("page");
    page.innerHTML = "";
    if (!state.doc) { fit(); return; }
    const blocks = state.doc.blocks;
    const p = (cls, text, i) => {
      const e = el("p", cls, text);
      if (i !== undefined) e.dataset.i = i;
      page.append(e);
      return e;
    };
    blocks.forEach((b, i) => { if (b.t === "title") p("title", b.text, i); });
    if (state.doc.kind === "brief") p("noindent blank-after-title", "");
    blocks.forEach((b, i) => {
      if (["title", "attachment", "signer", "date"].includes(b.t)) return;
      if (b.t === "table") {
        const t = el("table");
        t.dataset.i = i;
        b.rows.forEach((r) => { const tr = el("tr"); r.forEach((c) => tr.append(el("td", "", c))); t.append(tr); });
        page.append(t);
        p("noindent", "");
        return;
      }
      p(b.t === "h3" ? "body" : b.t, b.text, i);
    });
    const att = blocks.map((b, i) => [b, i]).filter(([b]) => b.t === "attachment");
    if (att.length) {
      p("body", "附件");
      att.forEach(([b, i], n) => p("body", `${n + 1}、${b.text}`, i));
    }
    const signoff = blocks.map((b, i) => [b, i]).filter(([b]) => b.t === "signer" || b.t === "date");
    if (signoff.length) {
      p("right", "");
      signoff.forEach(([b, i]) => p("right", b.t === "date" ? normalizeDate(b.text) : b.text, i));
    }
    if (state.selected !== null) {
      const t = page.querySelector(`[data-i="${state.selected}"]`);
      if (t) t.classList.add("hl");
    }
    fit();
  }

  function fit() {
    const right = $("right"), scaler = $("scaler"), page = $("page");
    const avail = right.clientWidth - 32;
    const scale = Math.min(1, avail / page.offsetWidth);
    scaler.style.transform = `scale(${scale})`;
    scaler.style.width = `${page.offsetWidth}px`;
    scaler.style.height = `${page.offsetHeight * scale}px`;
  }
  window.addEventListener("resize", fit);

  // ---- 事件 ----
  $("open").addEventListener("click", async () => {
    const path = await api().pick_docx();
    if (path) window.loadPath(path);
  });
  $("paste").addEventListener("click", () => { $("modal").hidden = false; $("paste-text").focus(); });
  $("paste-cancel").addEventListener("click", () => { $("modal").hidden = true; });
  $("paste-ok").addEventListener("click", async () => {
    const r = await api().parse_text($("paste-text").value);
    if (r.error) { notify(r.error); return; }
    $("modal").hidden = true;
    $("paste-text").value = "";
    setDoc(r);
  });
  document.querySelectorAll('input[name="kind"]').forEach((r) => r.addEventListener("change", () => {
    if (state.doc && r.checked) { state.doc.kind = r.value; renderPreview(); }
  }));
  $("export").addEventListener("click", async () => {
    if (!state.doc || state.busy) return;
    state.busy = true;
    $("export").disabled = true;
    const r = await api().export(state.doc);
    state.busy = false;
    $("export").disabled = false;
    if (r.error) notify(r.error);
    else if (r.path) notify(`已导出：${r.path}`, true, r.path);
  });
  $("notice-open").addEventListener("click", () => api().open_file($("notice-open").dataset.path));
  $("notice-close").addEventListener("click", () => { $("notice").hidden = true; });
  document.addEventListener("dragover", (e) => e.preventDefault());
  document.addEventListener("drop", (e) => e.preventDefault());

  renderList();
  renderPreview();
})();
