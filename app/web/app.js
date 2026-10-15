(() => {
  const $ = (id) => document.getElementById(id);
  const state = { files: [], targets: [], target: null, outDir: null, dpi: 200, busy: false };
  const api = () => window.pywebview.api;

  const STATE_TEXT = { queued: "排队中", running: "转换中…", done: "✅ 完成" };

  function esc(s) {
    return String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  }

  const valid = () => state.files.filter((f) => f.format);
  const pending = () => valid().filter((f) => f.state !== "done");
  const allImages = () => valid().length > 0 && valid().every((f) => f.format === "image");

  async function refreshTargets() {
    const paths = valid().map((f) => f.path);
    state.targets = paths.length ? await api().get_targets(paths) : [];
    if (!state.targets.some((t) => t.key === state.target)) state.target = null;
    render();
  }

  window.addFiles = async (paths) => {
    if (state.busy) return;
    const known = new Set(state.files.map((f) => f.path));
    const fresh = paths.filter((p) => !known.has(p));
    if (!fresh.length) return;
    const info = await api().describe(fresh);
    if (state.busy) return;
    const now = new Set(state.files.map((f) => f.path));
    for (const f of info.filter((f) => !now.has(f.path))) {
      state.files.push({ ...f, state: f.format ? "queued" : "error", message: f.format ? "" : "不支持的文件格式" });
    }
    $("summary").textContent = "";
    $("open-out").hidden = true;
    await refreshTargets();
  };

  window.onBackendEvent = (evt) => {
    if (evt.type === "status") {
      const f = state.running[evt.index];
      f.state = evt.state;
      f.message = evt.message || "";
      render();
    } else if (evt.type === "finished") {
      state.busy = false;
      $("summary").textContent = `完成 ${evt.ok} 个，失败 ${evt.failed} 个`;
      state.lastOut = evt.out_dir;
      $("open-out").hidden = !evt.out_dir;
      render();
    }
  };

  function render() {
    const has = state.files.length > 0;
    $("files-card").hidden = !has;
    $("settings").hidden = !has;
    $("actions").hidden = !has;
    $("file-count").textContent = has ? `（${state.files.length}）` : "";
    $("drop").classList.toggle("disabled", state.busy);

    $("files").innerHTML = state.files.map((f, i) => {
      const text = f.state === "error" ? `❌ ${f.message}` : STATE_TEXT[f.state];
      return `<li>
        <span class="name" title="${esc(f.path)}">${esc(f.name)}</span>
        <span class="tag">${esc(f.label || "未知")}</span>
        <span class="state ${f.state}" title="${esc(text)}">${esc(text)}</span>
        <button class="remove" data-i="${i}" title="移除" ${state.busy ? "disabled" : ""}>×</button>
      </li>`;
    }).join("");

    $("targets").innerHTML = state.targets.map((t) =>
      `<button data-key="${t.key}" class="${t.key === state.target ? "on" : ""}" ${state.busy ? "disabled" : ""}>${esc(t.label)}</button>`
    ).join("");
    $("no-targets").hidden = !(valid().length && !state.targets.length);

    $("dpi-row").hidden = state.target !== "image";
    $("merge-row").hidden = !(state.target === "pdf" && allImages());
    document.querySelectorAll("#dpi button").forEach((b) => {
      b.classList.toggle("on", Number(b.dataset.dpi) === state.dpi);
      b.disabled = state.busy;
    });
    document.querySelectorAll("#settings input").forEach((el) => (el.disabled = state.busy));
    $("clear").disabled = state.busy;
    $("out-path").textContent = state.outDir || "";
    $("start").disabled = state.busy || !state.target || !pending().length;
    $("start").textContent = state.busy ? "转换中…" : "开始转换";
  }

  async function pick() {
    if (state.busy) return;
    const paths = await api().pick_files();
    if (paths.length) window.addFiles(paths);
  }

  function bind() {
    const drop = $("drop");
    drop.addEventListener("click", pick);
    drop.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") pick(); });
    ["dragenter", "dragover"].forEach((t) => document.addEventListener(t, (e) => { e.preventDefault(); drop.classList.add("over"); }));
    ["dragleave", "drop"].forEach((t) => document.addEventListener(t, (e) => { e.preventDefault(); drop.classList.remove("over"); }));

    $("files").addEventListener("click", (e) => {
      const b = e.target.closest(".remove");
      if (!b || state.busy) return;
      state.files.splice(Number(b.dataset.i), 1);
      refreshTargets();
    });
    $("clear").addEventListener("click", () => { state.files = []; $("summary").textContent = ""; $("open-out").hidden = true; refreshTargets(); });
    $("targets").addEventListener("click", (e) => {
      const b = e.target.closest("button");
      if (b) { state.target = b.dataset.key; render(); }
    });
    $("dpi").addEventListener("click", (e) => {
      const b = e.target.closest("button");
      if (b) { state.dpi = Number(b.dataset.dpi); render(); }
    });
    document.querySelectorAll('input[name="out"]').forEach((r) => r.addEventListener("click", async () => {
      if (r.value === "custom") {
        const dir = await api().pick_folder();  // 每次点击都可重新选择
        if (dir) state.outDir = dir;
        if (!state.outDir) document.querySelector('input[name="out"][value="same"]').checked = true;
      } else {
        state.outDir = null;
      }
      render();
    }));
    $("start").addEventListener("click", () => {
      const files = pending();  // 已完成的文件不再重复转换
      files.forEach((f) => { f.state = "queued"; f.message = ""; });
      state.running = files;
      state.busy = true;
      $("summary").textContent = "";
      $("open-out").hidden = true;
      render();
      api().start(files.map((f) => f.path), state.target, state.outDir,
        { dpi: state.dpi, merge_images: $("merge").checked });
    });
    $("open-out").addEventListener("click", () => api().open_folder(state.lastOut));
  }

  bind();
  render();
})();
